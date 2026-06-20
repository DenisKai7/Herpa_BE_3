from __future__ import annotations

from dataclasses import dataclass

from app.services.recommendation.symptom_aliases import expand_symptoms

MAX_PRIMARY_TERMS = 5
MAX_EXPANDED_TERMS = 15


@dataclass(frozen=True)
class RecommendationTerms:
    primary_terms: list[str]
    expanded_terms: list[str]


def normalize_term(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _extract_primary_from_text(text: str) -> list[str]:
    normalized = normalize_term(text)
    if not normalized:
        return []
    for separator in (",", ";", " dengan ", " dan "):
        normalized = normalized.replace(separator, "|")
    return [part for part in (normalize_term(item) for item in normalized.split("|")) if len(part) >= 3]


def _dedupe_limited(values: list[str], limit: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_term(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def extract_recommendation_terms(complaint: str, symptoms: list[str]) -> RecommendationTerms:
    primary_seed = [*symptoms, *_extract_primary_from_text(complaint)]
    primary_terms = _dedupe_limited(primary_seed, MAX_PRIMARY_TERMS)
    expanded_terms = _dedupe_limited([*primary_terms, *expand_symptoms(primary_terms)], MAX_EXPANDED_TERMS)
    return RecommendationTerms(primary_terms=primary_terms, expanded_terms=expanded_terms)
