from typing import Any


def validate_grounding(
    answer: str, retrieval: dict[str, Any], sources: list[dict[str, Any]]
) -> dict[str, Any]:
    facts = retrieval.get("facts", [])
    if not facts and not sources:
        return {
            "status": "insufficient",
            "confidence": 0.25,
            "warnings": ["Data terverifikasi yang tersedia belum mencukupi."],
        }
    confidence = min(0.95, 0.55 + 0.04 * min(len(facts) + len(sources), 10))
    return {"status": "grounded" if facts else "partial", "confidence": round(confidence, 2), "warnings": []}
