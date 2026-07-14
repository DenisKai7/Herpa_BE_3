"""LLM Judge — evaluates Answer Relevancy metric for GraphRAG evaluation.

Optimized configuration:
  - Single prompt, JSON-only output, 120 token limit
  - temperature=0, top_p=0.1 for deterministic scoring
  - Timeout only retries (not parse errors)
  - Robust 6-stage JSON parser with sanitization, repair, and debug logging
  - Input validation: empty inputs → SKIP, not 0.0
"""

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_DEBUG_DIR = Path(__file__).parent.parent / "debug"

# ─── Judge prompt (Answer Relevancy only) ────────────────────────────────────

_JUDGE_PROMPT = """Anda adalah evaluator sistem RAG untuk tanaman herbal Indonesia.
Evaluasi relevansi jawaban terhadap pertanyaan. Berikan skor 0.0-1.0.

PERTANYAAN: {question}

JAWABAN LLM:
{answer}

JAWABAN BENAR (Ground Truth):
{ground_truth}

Jawab HANYA dengan JSON (tanpa markdown, tanpa penjelasan):
{{
  "answer_relevancy": {{"score": 0.0, "reason": "..."}}
}}

Kriteria:
answer_relevancy: Seberapa relevan jawaban dengan pertanyaan? (0=tidak relevan, 1=sangat relevan)

PENTING:
- Berikan HANYA JSON object. Jangan tambahkan teks lain.
- Hanya evaluasi answer_relevancy. Jangan tambahkan metric lain.
- Jika jawaban kosong, berikan skor 0.0."""


JUDGE_PROMPT_VERSION = "v4.0"
JUDGE_MODEL = "local-llm"

# Required metric keys with defaults (only answer_relevancy)
_METRIC_DEFAULTS = {
    "answer_relevancy": 0.0,
}


@dataclass
class JudgeResult:
    """Result from judge call.

    Only answer_relevancy score. Always float 0.0–1.0, never None.
    """
    answer_relevancy: float = 0.0
    raw: dict[str, Any] | None = None
    success: bool = True
    skipped: bool = False
    skip_reason: str = ""
    error: str | None = None
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    retries: int = 0
    status: str = "OK"

    @property
    def metric_names(self) -> list[str]:
        return ["answer_relevancy"]

    @property
    def valid_score_count(self) -> int:
        """Count how many metrics have non-zero scores (0.0 indicates missing/failed)."""
        return sum(1 for m in self.metric_names if getattr(self, m) > 0.0)

    def to_dict(self) -> dict[str, float]:
        return {m: getattr(self, m) for m in self.metric_names}


# ─── Sanitizer ───────────────────────────────────────────────────────────────

def _sanitize(text: str) -> str:
    """Remove noise before JSON parsing."""
    if not text:
        return ""

    # Remove BOM
    text = text.replace("﻿", "")

    # Remove markdown fences but keep inner content
    text = re.sub(r'```(?:json)?\s*\n?', '', text)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)

    # Replace smart quotes with straight quotes
    text = text.replace('“', '"').replace('”', '"')
    text = text.replace('‘', "'").replace('’', "'")
    text = text.replace('«', '"').replace('»', '"')

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Collapse multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


# ─── JSON Repair ─────────────────────────────────────────────────────────────

def _repair_json(text: str) -> str:
    """Attempt to repair common JSON issues."""
    if not text:
        return text

    # Remove trailing commas before } or ]
    text = re.sub(r',\s*([\]}])', r'\1', text)

    # Remove trailing comma at end of content
    text = re.sub(r',\s*$', '', text.strip())

    # Fix missing closing braces: count open vs close
    open_count = text.count('{')
    close_count = text.count('}')
    if open_count > close_count:
        text = text.rstrip() + '}' * (open_count - close_count)

    # Fix missing closing brackets
    open_b = text.count('[')
    close_b = text.count(']')
    if open_b > close_b:
        text = text.rstrip() + ']' * (open_b - close_b)

    # Fix unterminated strings
    unescaped_quotes = len(re.findall(r'(?<!\\)"', text))
    if unescaped_quotes % 2 != 0:
        last_quote = text.rfind('"')
        if last_quote != -1:
            brace_pos = text.rfind('}')
            if brace_pos > last_quote:
                text = text[:brace_pos] + '"' + text[brace_pos:]
            else:
                text = text + '"'

    return text


# ─── Multi-stage JSON Parser ─────────────────────────────────────────────────

def _parse_json_robust(text: str) -> dict:
    """Extract JSON from LLM response with 6-stage fallback."""
    if not text or not text.strip():
        return {}

    text = _sanitize(text)

    # Stage 1: Direct parse
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, ValueError):
        pass

    # Stage 2: Strip markdown fences
    fence_pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```'
    match = re.search(fence_pattern, text)
    if match:
        inner = match.group(1).strip()
        try:
            result = json.loads(inner)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        repaired = _repair_json(inner)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Stage 3: Brace balancing
    first_brace = text.find('{')
    if first_brace != -1:
        depth = 0
        end_pos = -1
        in_string = False
        escape_next = False
        for i in range(first_brace, len(text)):
            ch = text[i]
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end_pos = i
                    break

        if end_pos > first_brace:
            candidate = text[first_brace:end_pos + 1]
            try:
                result = json.loads(candidate)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass
            repaired = _repair_json(candidate)
            try:
                result = json.loads(repaired)
                if isinstance(result, dict):
                    return result
            except (json.JSONDecodeError, ValueError):
                pass

        candidate = text[first_brace:]
        repaired = _repair_json(candidate)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Stage 4: Regex extract first JSON object
    brace_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if brace_match:
        candidate = brace_match.group(0)
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass
        repaired = _repair_json(candidate)
        try:
            result = json.loads(repaired)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # Stage 5: Extract key-value pairs with regex
    kv_pattern = r'"(\w+)"\s*:\s*(\{[^}]*\}|\d+\.?\d*|"[^"]*"|true|false|null)'
    matches = re.findall(kv_pattern, text)
    if matches:
        result = {}
        for key, val_str in matches:
            try:
                result[key] = json.loads(val_str)
            except (json.JSONDecodeError, ValueError):
                result[key] = val_str.strip('"')
        if result:
            return result

    # Stage 6: Final failure
    return {}


def _extract_score_safe(data: dict, key: str) -> float:
    """Extract score from metric dict. Always returns float 0.0–1.0, never None."""
    val = data.get(key)
    if val is None:
        return 0.0

    # Direct numeric
    if isinstance(val, (int, float)):
        try:
            return max(0.0, min(1.0, float(val)))
        except (ValueError, TypeError):
            return 0.0

    # Nested dict with "score" or "value" key
    if isinstance(val, dict):
        score_val = val.get("score") or val.get("value")
        if score_val is None:
            return 0.0
        try:
            return max(0.0, min(1.0, float(score_val)))
        except (ValueError, TypeError):
            return 0.0

    # String that might be a number
    if isinstance(val, str):
        try:
            return max(0.0, min(1.0, float(val)))
        except (ValueError, TypeError):
            return 0.0

    return 0.0


_METRIC_KEYS = ["answer_relevancy"]


def _normalize_to_metrics(data: dict) -> dict:
    """Normalize parsed JSON to standard format.

    Handles:
      Format A: {"answer_relevancy": {"score": 0.9, "reason": "..."}}
      Format B: {"answer_relevancy": 0.9}
      Format C: {"score": 0.9, "reason": "..."}
      Format D: {"metrics": {"answer_relevancy": 0.9}}
      Format E: {"answer_relevancy": {"score": 0.9}} (partial)
    """
    if not data:
        return {}

    # Format D: nested "metrics" key
    if "metrics" in data and isinstance(data["metrics"], dict):
        data = data["metrics"]

    # Format C: top-level "score" key, no metric keys
    has_metric_keys = any(k in data for k in _METRIC_KEYS)
    if "score" in data and not has_metric_keys:
        score_val = data["score"]
        reason = data.get("reason", "")
        return {"answer_relevancy": {"score": score_val, "reason": reason}}

    # Format A/B/E: has metric keys
    result = {}
    for key in _METRIC_KEYS:
        val = data.get(key)
        if val is None:
            result[key] = None
        elif isinstance(val, dict):
            result[key] = val
        elif isinstance(val, (int, float)):
            result[key] = {"score": val, "reason": ""}
        elif isinstance(val, str):
            try:
                result[key] = {"score": float(val), "reason": ""}
            except (ValueError, TypeError):
                result[key] = None
        else:
            result[key] = None

    return result


def _validate_and_fill_scores(scores: dict[str, float]) -> dict[str, float]:
    """Validate metric keys exist and are valid floats 0.0–1.0."""
    result = {}
    for key in _METRIC_KEYS:
        val = scores.get(key)
        if val is None or not isinstance(val, (int, float)):
            result[key] = 0.0
        else:
            result[key] = max(0.0, min(1.0, float(val)))
    return result


def _save_debug_output(query_id: int | str, prompt: str, raw_text: str, parsed: dict, error: str):
    """Save debug output when parsing fails."""
    try:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        path = _DEBUG_DIR / f"judge_raw_q{query_id}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("=== JUDGE DEBUG OUTPUT ===\n\n")
            f.write(f"--- PROMPT ({len(prompt)} chars) ---\n")
            f.write(prompt[:3000] + "\n\n")
            f.write(f"--- RAW RESPONSE ({len(raw_text)} chars) ---\n")
            f.write(raw_text[:5000] + "\n\n")
            f.write(f"--- PARSED JSON ---\n")
            f.write(json.dumps(parsed, indent=2, ensure_ascii=False) + "\n\n")
            f.write(f"--- ERROR ---\n")
            f.write(error + "\n")
        logger.info(f"Debug output saved: {path}")
    except Exception as e:
        logger.warning(f"Failed to save debug output: {e}")


# ─── Validation ──────────────────────────────────────────────────────────────

def _validate_inputs(
    question: str,
    answer: str,
    ground_truth: str,
) -> tuple[bool, str]:
    """Validate inputs before LLM call. Returns (is_valid, skip_reason)."""
    if not question or not question.strip():
        return False, "Empty question"
    if not answer or not answer.strip():
        return False, "Empty answer"
    return True, ""


# ─── Main judge function ────────────────────────────────────────────────────

async def evaluate_answer_relevancy(
    client: AsyncOpenAI,
    model: str,
    question: str,
    answer: str,
    ground_truth: str,
    timeout: float = 120.0,
    max_retries: int = 2,
) -> JudgeResult:
    """Evaluate Answer Relevancy metric in a single LLM call.

    Key design:
    - Parse errors do NOT trigger LLM retries (fixed locally)
    - Timeout and connection errors retry with exponential backoff
    - Returns raw_text in result.raw for debug saving
    """
    is_valid, skip_reason = _validate_inputs(question, answer, ground_truth)
    if not is_valid:
        logger.warning(f"Judge SKIPPED: {skip_reason}")
        return JudgeResult(skipped=True, skip_reason=skip_reason, success=False, status="SKIPPED")

    gt_text = ground_truth[:1000] if ground_truth else "Tidak tersedia"

    prompt = _JUDGE_PROMPT.format(
        question=question,
        answer=answer[:1500],
        ground_truth=gt_text,
    )

    prompt_chars = len(prompt)
    prompt_tokens_est = prompt_chars // 4
    logger.info(f"Judge prompt: {prompt_chars} chars, ~{prompt_tokens_est} tokens")

    total_prompt_tokens = 0
    total_completion_tokens = 0
    retries_done = 0
    last_error = ""
    raw_text = ""

    for attempt in range(max_retries + 1):
        if attempt > 0:
            backoff = min(2 ** attempt, 8)
            logger.info(f"Retry {attempt}/{max_retries}, backoff {backoff}s")
            await asyncio.sleep(backoff)

        t0 = time.perf_counter()

        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                top_p=0.1,
                max_tokens=120,
                timeout=timeout,
            )
            latency_ms = (time.perf_counter() - t0) * 1000

            usage = resp.usage
            if usage:
                total_prompt_tokens = usage.prompt_tokens or 0
                total_completion_tokens = usage.completion_tokens or 0

            raw_text = resp.choices[0].message.content.strip()
            data = _parse_json_robust(raw_text)

            if not data:
                last_error = "JSON parse failed after 6-stage parser"
                logger.warning(f"Judge parse failed: {raw_text[:200]}")
                _save_debug_output(
                    query_id=f"unknown_{attempt}",
                    prompt=prompt,
                    raw_text=raw_text,
                    parsed=data,
                    error=last_error,
                )
                return JudgeResult(
                    success=False, error=last_error, latency_ms=latency_ms,
                    prompt_tokens=total_prompt_tokens, completion_tokens=total_completion_tokens,
                    total_tokens=total_prompt_tokens + total_completion_tokens,
                    retries=retries_done, status="JUDGE_ERROR",
                    raw={"raw_text": raw_text[:2000], "prompt": prompt[:2000]},
                )

            logger.info(f"Judge raw JSON keys: {list(data.keys())}")
            data = _normalize_to_metrics(data)

            raw_scores = {
                "answer_relevancy": _extract_score_safe(data, "answer_relevancy"),
            }

            found_metrics = [k for k, v in raw_scores.items() if v > 0.0]
            missing_metrics = [k for k, v in raw_scores.items() if v == 0.0]
            if missing_metrics:
                logger.warning(f"Judge metrics with 0.0 score: {missing_metrics}")

            scores = _validate_and_fill_scores(raw_scores)

            logger.info(
                f"Judge OK ({len(found_metrics)}/1 metric > 0): "
                f"ans_rel={scores['answer_relevancy']:.2f} ({latency_ms:.0f}ms)"
            )

            return JudgeResult(
                answer_relevancy=scores["answer_relevancy"],
                raw={"parsed": data, "raw_text": raw_text[:2000], "prompt": prompt[:2000]},
                success=True, latency_ms=latency_ms,
                prompt_tokens=total_prompt_tokens, completion_tokens=total_completion_tokens,
                total_tokens=total_prompt_tokens + total_completion_tokens,
                retries=retries_done, status="OK",
            )

        except asyncio.TimeoutError:
            latency_ms = (time.perf_counter() - t0) * 1000
            last_error = f"JUDGE_TIMEOUT after {timeout}s (attempt {attempt + 1})"
            logger.warning(last_error)
            retries_done += 1
            if attempt < max_retries:
                continue
            return JudgeResult(
                success=False, error=last_error, latency_ms=latency_ms,
                prompt_tokens=total_prompt_tokens, completion_tokens=0,
                total_tokens=total_prompt_tokens, retries=retries_done,
                status="JUDGE_TIMEOUT",
                raw={"raw_text": raw_text[:2000], "prompt": prompt[:2000]},
            )

        except Exception as e:
            latency_ms = (time.perf_counter() - t0) * 1000
            last_error = f"LLM error: {type(e).__name__}: {e} (attempt {attempt + 1})"
            logger.warning(last_error)
            retries_done += 1
            if attempt < max_retries:
                continue
            return JudgeResult(
                success=False, error=last_error, latency_ms=latency_ms,
                prompt_tokens=total_prompt_tokens, completion_tokens=0,
                total_tokens=total_prompt_tokens, retries=retries_done,
                status="JUDGE_ERROR",
                raw={"raw_text": raw_text[:2000], "prompt": prompt[:2000]},
            )

    return JudgeResult(
        success=False, error=last_error or "Unknown error",
        status="JUDGE_ERROR", retries=retries_done,
        raw={"raw_text": raw_text[:2000], "prompt": prompt[:2000]},
    )


# Backward-compatible alias
evaluate_combined = evaluate_answer_relevancy
