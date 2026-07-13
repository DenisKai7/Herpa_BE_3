"""Hallucination detection: sentences in answer not supported by retrieved context."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

HALLUCINATION_PROMPT = """Anda adalah evaluator deteksi halusinasi. Periksa apakah setiap kalimat dalam jawaban didukung oleh konteks yang diambil.

Konteks yang diambil:
{context}

Jawaban LLM:
{answer}

Untuk setiap kalimat dalam jawaban, tentukan apakah kalimat tersebut:
- "supported": didukung oleh konteks
- "unsupported": TIDAK didukung oleh konteks (potensi halusinasi)

Jawab HANYA dengan JSON array: [{{"sentence": "<kalimat>", "status": "supported|unsupported", "reason": "<alasan>"}}]"""


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Handles Indonesian punctuation."""
    # Split on sentence-ending punctuation
    sentences = re.split(r'[.!?]+', text)
    # Clean and filter
    cleaned = []
    for s in sentences:
        s = s.strip()
        if len(s) >= 10:  # Minimum sentence length
            cleaned.append(s)
    return cleaned


async def detect_hallucinations_llm(
    answer: str,
    contexts: list[str],
    llm_client: Any,
    model: str,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Detect hallucinations using LLM judge.

    Returns dict with hallucination_count, total_sentences, rate, and details.
    """
    if not answer:
        return {
            "hallucination_count": 0,
            "total_sentences": 0,
            "rate": 0.0,
            "details": [],
            "method": "llm_judge",
        }

    combined_context = "\n---\n".join(contexts[:5])[:3000]
    prompt = HALLUCINATION_PROMPT.format(context=combined_context, answer=answer[:3000])

    try:
        response = await llm_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000,
            timeout=timeout,
        )
        content = response.choices[0].message.content.strip()

        # Extract JSON from response
        if "```" in content:
            content = content.split("```")[1].strip()
            if content.startswith("json"):
                content = content[4:].strip()

        details = json.loads(content)
        if not isinstance(details, list):
            details = []

        hallucination_count = sum(1 for d in details if d.get("status") == "unsupported")
        total = len(details)

        return {
            "hallucination_count": hallucination_count,
            "total_sentences": total,
            "rate": hallucination_count / total if total > 0 else 0.0,
            "details": details,
            "method": "llm_judge",
        }
    except Exception as e:
        logger.warning(f"Hallucination detection failed: {e}")
        return detect_hallucinations_heuristic(answer, contexts)


def detect_hallucinations_heuristic(
    answer: str,
    contexts: list[str],
) -> dict[str, Any]:
    """Heuristic hallucination detection based on keyword coverage.

    A sentence is flagged if it contains domain-specific terms not found in context.
    """
    sentences = split_sentences(answer)
    if not sentences:
        return {
            "hallucination_count": 0,
            "total_sentences": 0,
            "rate": 0.0,
            "details": [],
            "method": "heuristic",
        }

    # Build context keyword set
    context_text = " ".join(contexts).lower()
    context_words = set(re.findall(r'[a-z]+', context_text))

    # Domain-specific terms that should appear in context if mentioned in answer
    domain_terms = {
        "antiinflamasi", "antioksidan", "antimikroba", "hepatoprotektif",
        "analgesik", "antipiretik", "sedatif", "adaptogen", "imunostimulan",
        "antikoagulan", "antitrombotik", "bronkodilator", "karminatif",
        "antispasmodik", "astringen", "diuretik", "antidiabetik",
        "kurkumin", "gingerol", "allicin", "andrographolide", "asiaticoside",
        "ginsenosida", "quercetin", "eugenol", "phyllanthin",
        "kunyit", "jahe", "temulawak", "kencur", "sambiloto", "pegagan",
        "daun sirih", "meniran", "bawang putih", "ginseng",
    }

    details = []
    hallucination_count = 0

    for sentence in sentences:
        sentence_lower = sentence.lower()
        sentence_words = set(re.findall(r'[a-z]+', sentence_lower))

        # Check if key domain terms in the sentence are supported by context
        found_terms = sentence_words & domain_terms
        unsupported_terms = [t for t in found_terms if t not in context_words]

        # If more than half of domain terms are unsupported, flag as hallucination
        if found_terms and len(unsupported_terms) > len(found_terms) / 2:
            status = "unsupported"
            hallucination_count += 1
            reason = f"Terms not in context: {', '.join(unsupported_terms[:3])}"
        else:
            status = "supported"
            reason = "Key terms found in context"

        details.append({
            "sentence": sentence[:200],
            "status": status,
            "reason": reason,
        })

    return {
        "hallucination_count": hallucination_count,
        "total_sentences": len(sentences),
        "rate": hallucination_count / len(sentences) if sentences else 0.0,
        "details": details,
        "method": "heuristic",
    }


async def compute_hallucination_rate(
    answer: str,
    contexts: list[str],
    llm_client: Any = None,
    model: str = "",
) -> dict[str, Any]:
    """Compute hallucination rate for a single query.

    Uses LLM judge if available, falls back to heuristic.
    """
    if llm_client and model:
        return await detect_hallucinations_llm(answer, contexts, llm_client, model)
    return detect_hallucinations_heuristic(answer, contexts)


def aggregate_hallucination_metrics(all_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate hallucination metrics across all queries."""
    if not all_results:
        return {"total_hallucinations": 0, "total_sentences": 0, "rate": 0.0}

    total_hallucinations = sum(r.get("hallucination_count", 0) for r in all_results)
    total_sentences = sum(r.get("total_sentences", 0) for r in all_results)

    return {
        "total_hallucinations": total_hallucinations,
        "total_sentences": total_sentences,
        "rate": round(total_hallucinations / total_sentences, 4) if total_sentences > 0 else 0.0,
    }
