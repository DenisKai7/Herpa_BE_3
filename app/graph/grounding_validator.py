from typing import Any


def validate_grounding(
    answer: str, retrieval: dict[str, Any], sources: list[dict[str, Any]],
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    facts = retrieval.get("facts", [])
    has_vlm = any(att.get("plant_candidates") for att in (attachments or []))

    if not facts and not sources and not has_vlm:
        return {
            "status": "insufficient",
            "confidence": 0.25,
            "warnings": ["Data terverifikasi yang tersedia belum mencukupi."],
        }

    if has_vlm and not facts:
        return {
            "status": "vlm_identified",
            "confidence": 0.60,
            "warnings": ["Identifikasi berdasarkan analisis visual. Verifikasi dengan data botani belum tersedia."],
        }

    confidence = min(0.95, 0.55 + 0.04 * min(len(facts) + len(sources), 10))
    if has_vlm:
        confidence = min(0.95, confidence + 0.10)
    return {"status": "grounded" if facts else "partial", "confidence": round(confidence, 2), "warnings": []}
