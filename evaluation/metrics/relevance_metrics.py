"""Context Relevance and Answer Relevance metrics using LLM judge and embedding similarity."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# LLM Judge prompts
CONTEXT_RELEVANCE_PROMPT = """Anda adalah evaluator sistem RAG. Tentukan seberapa relevan konteks yang diambil terhadap query pengguna.

Query: {query}

Konteks yang diambil:
{context}

Beri skor 0-1 berdasarkan relevansi konteks terhadap query.
Jawab HANYA dengan JSON: {{"score": <float>, "reason": "<alasan singkat>"}}"""

ANSWER_RELEVANCE_PROMPT = """Anda adalah evaluator sistem RAG. Tentukan seberapa relevan jawaban LLM terhadap query pengguna.

Query: {query}

Jawaban LLM:
{answer}

Beri skor 0-1 berdasarkan kesesuaian jawaban dengan query.
Jawab HANYA dengan JSON: {{"score": <float>, "reason": "<alasan singtok>"}}"""


async def _llm_judge_score(
    llm_client: Any,
    prompt: str,
    model: str,
    timeout: float = 30.0,
) -> tuple[float, str]:
    """Call LLM to judge relevance. Returns (score, reason)."""
    try:
        response = await llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=200,
            timeout=timeout,
        )
        content = response.choices[0].message.content.strip()
        # Extract JSON from response
        if "```" in content:
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        parsed = json.loads(content)
        score = float(parsed.get("score", 0.0))
        reason = str(parsed.get("reason", ""))
        return max(0.0, min(1.0, score)), reason
    except Exception as e:
        logger.warning(f"LLM judge failed: {e}")
        return 0.0, f"Error: {e}"


def _keyword_overlap_score(query: str, text: str) -> float:
    """Simple keyword overlap as fallback when LLM is unavailable."""
    query_tokens = set(query.lower().split())
    text_tokens = set(text.lower().split())
    if not query_tokens:
        return 0.0
    overlap = query_tokens & text_tokens
    # Remove common stopwords
    stopwords = {"apa", "yang", "dan", "untuk", "dengan", "ini", "itu", "dari", "pada", "adalah", "di", "ke", "oleh"}
    meaningful = overlap - stopwords
    return min(1.0, len(meaningful) / max(1, len(query_tokens - stopwords)))


async def compute_context_relevance(
    query: str,
    contexts: list[str],
    llm_client: Any = None,
    model: str = "",
) -> dict[str, Any]:
    """Compute context relevance score for a single query.

    Uses LLM judge if available, falls back to keyword overlap.
    """
    if not contexts:
        return {"score": 0.0, "method": "no_context", "reason": "No context retrieved"}

    combined_context = "\n---\n".join(contexts[:5])  # Limit to top 5

    if llm_client and model:
        prompt = CONTEXT_RELEVANCE_PROMPT.format(query=query, context=combined_context[:3000])
        score, reason = await _llm_judge_score(llm_client, prompt, model)
        return {"score": score, "method": "llm_judge", "reason": reason}

    # Fallback: keyword overlap
    score = _keyword_overlap_score(query, combined_context)
    return {"score": score, "method": "keyword_overlap", "reason": "Fallback method"}


async def compute_answer_relevance(
    query: str,
    answer: str,
    llm_client: Any = None,
    model: str = "",
) -> dict[str, Any]:
    """Compute answer relevance score for a single query.

    Uses LLM judge if available, falls back to keyword overlap.
    """
    if not answer:
        return {"score": 0.0, "method": "no_answer", "reason": "No answer generated"}

    if llm_client and model:
        prompt = ANSWER_RELEVANCE_PROMPT.format(query=query, answer=answer[:3000])
        score, reason = await _llm_judge_score(llm_client, prompt, model)
        return {"score": score, "method": "llm_judge", "reason": reason}

    # Fallback: keyword overlap
    score = _keyword_overlap_score(query, answer)
    return {"score": score, "method": "keyword_overlap", "reason": "Fallback method"}


def aggregate_relevance_metrics(all_scores: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate relevance metrics across all queries."""
    if not all_scores:
        return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0}

    scores = [s["score"] for s in all_scores]
    scores.sort()

    n = len(scores)
    mean = sum(scores) / n
    median = scores[n // 2] if n % 2 == 1 else (scores[n // 2 - 1] + scores[n // 2]) / 2

    return {
        "mean": round(mean, 4),
        "median": round(median, 4),
        "min": round(min(scores), 4),
        "max": round(max(scores), 4),
    }
