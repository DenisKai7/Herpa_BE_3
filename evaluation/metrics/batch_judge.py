"""Combined LLM Judge — evaluates ALL 6 reasoning metrics in ONE LLM call.

Replaces 6 separate DeepEval calls with a single structured prompt.
Target: 800ms per query instead of 4800ms.
"""

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ─── Combined prompt ─────────────────────────────────────────────────────────

_COMBINED_PROMPT = """Anda adalah evaluator sistem RAG. Evaluasi jawaban berdasarkan 6 kriteria.
Berikan skor 0.0-1.0 untuk setiap kriteria.

PERTANYAAN: {question}

KONTEKS YANG DIAMBIL:
{context}

JAWABAN LLM:
{answer}

JAWABAN BENAR (Ground Truth):
{ground_truth}

Evaluasi 6 kriteria berikut dan jawab HANYA dengan JSON:
{{
  "answer_relevancy": {{"score": <float>, "reason": "..."}},
  "faithfulness": {{"score": <float>, "reason": "..."}},
  "contextual_precision": {{"score": <float>, "reason": "..."}},
  "contextual_recall": {{"score": <float>, "reason": "..."}},
  "contextual_relevancy": {{"score": <float>, "reason": "..."}},
  "hallucination_rate": {{"score": <float>, "reason": "..."}}
}}

Kriteria:
1. answer_relevancy: Seberapa relevan jawaban dengan pertanyaan?
2. faithfulness: Apakah jawaban didukung oleh konteks?
3. contextual_precision: Berapa banyak konteks yang relevan dengan pertanyaan?
4. contextual_recall: Seberapa lengkap konteks mencakup informasi yang dibutuhkan?
5. contextual_relevancy: Seberapa relevan konteks secara keseluruhan dengan pertanyaan?
6. hallucination_rate: 1.0 = tidak ada halusinasi, 0.0 = semua halusinasi"""


@dataclass
class JudgeResult:
    """Result from combined judge call."""
    answer_relevancy: float = 0.0
    faithfulness: float = 0.0
    contextual_precision: float = 0.0
    contextual_recall: float = 0.0
    contextual_relevancy: float = 0.0
    hallucination_score: float = 0.0  # 1.0 = no hallucination
    raw: dict[str, Any] | None = None
    success: bool = True
    error: str | None = None
    latency_ms: float = 0.0


def _parse_json(text: str) -> dict:
    """Extract JSON from LLM response."""
    # Strip markdown fences
    if "```" in text:
        text = text.split("```")[1].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _extract_score(data: dict, key: str) -> float:
    """Extract score from metric dict, handling nested and flat formats."""
    val = data.get(key, {})
    if isinstance(val, (int, float)):
        return max(0.0, min(1.0, float(val)))
    if isinstance(val, dict):
        return max(0.0, min(1.0, float(val.get("score", 0.0))))
    return 0.0


async def evaluate_combined(
    client: AsyncOpenAI,
    model: str,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
    timeout: float = 30.0,
) -> JudgeResult:
    """Evaluate ALL 6 metrics in a SINGLE LLM call.

    This is the key optimization: 1 call instead of 6.
    """
    if not answer:
        return JudgeResult(success=False, error="No answer")

    ctx_text = "\n---\n".join(contexts[:5])[:3000]
    prompt = _COMBINED_PROMPT.format(
        question=question,
        context=ctx_text,
        answer=answer[:2000],
        ground_truth=ground_truth[:1500] if ground_truth else "Tidak tersedia",
    )

    import time
    t0 = time.perf_counter()

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=600,
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        text = resp.choices[0].message.content.strip()
        data = _parse_json(text)

        if not data:
            return JudgeResult(
                success=False,
                error="Failed to parse JSON response",
                latency_ms=latency_ms,
            )

        return JudgeResult(
            answer_relevancy=_extract_score(data, "answer_relevancy"),
            faithfulness=_extract_score(data, "faithfulness"),
            contextual_precision=_extract_score(data, "contextual_precision"),
            contextual_recall=_extract_score(data, "contextual_recall"),
            contextual_relevancy=_extract_score(data, "contextual_relevancy"),
            hallucination_score=1.0 - _extract_score(data, "hallucination_rate"),
            raw=data,
            success=True,
            latency_ms=latency_ms,
        )

    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        logger.warning(f"Combined judge failed: {e}")
        return JudgeResult(
            success=False,
            error=str(e),
            latency_ms=latency_ms,
        )
