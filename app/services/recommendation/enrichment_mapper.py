from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.json_safety import json_safe

ENRICHMENT_KEYS = (
    "traditional_uses",
    "preparation_methods",
    "usage_guidelines",
    "safety_warnings",
    "plant_parts",
    "storage_guidelines",
    "myth_facts",
    "quality_standards",
    "clinical_guidelines",
    "drug_interactions",
    "contraindications",
    "pharmacokinetic_profiles",
    "research_topics",
    "claims",
    "related_symptoms",
)

CLINICAL_DOSE_NOTICE = (
    "Dosis klinis detail tidak ditampilkan untuk penggunaan mandiri. Gunakan sesuai batas wajar dan "
    "konsultasikan kepada tenaga kesehatan bila memiliki kondisi khusus."
)


def empty_enrichment() -> dict[str, list[Any]]:
    return {key: [] for key in ENRICHMENT_KEYS}


def remove_empty_items(
    items: list[dict] | None,
    required_keys: tuple[str, ...] = ("id", "title", "name", "description"),
) -> list[dict]:
    cleaned: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        if not any(item.get(key) for key in required_keys):
            continue
        cleaned.append(json_safe(item))
    return cleaned


def flatten_unique(values: list[Any] | None) -> list[Any]:
    seen: set[str] = set()
    result: list[Any] = []
    for value in values or []:
        nested = value if isinstance(value, list) else [value]
        for sub in nested:
            key = str(sub)
            if sub and key not in seen:
                seen.add(key)
                result.append(sub)
    return result


def dedupe_sources(sources: list[dict] | None) -> list[dict]:
    seen: set[str] = set()
    result: list[dict] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        key = str(source.get("source_id") or source.get("identifier") or source.get("title") or source)
        if key in seen:
            continue
        seen.add(key)
        result.append(json_safe(source))
    return result


def merge_nested_sources(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized = dict(item)
        normalized["sources"] = dedupe_sources(normalized.get("sources", []))
        result.append(normalized)
    return result


def _merge_list_field(items: list[dict], field: str) -> list[dict]:
    by_key: dict[str, dict] = {}
    for item in items:
        key = str(item.get("id") or item.get("claim_id") or item.get("title") or item.get("name") or item)
        if key not in by_key:
            by_key[key] = dict(item)
            continue
        existing = by_key[key]
        existing[field] = flatten_unique([existing.get(field), item.get(field)])
        if "sources" in existing or "sources" in item:
            existing["sources"] = dedupe_sources([*(existing.get("sources") or []), *(item.get("sources") or [])])
    return list(by_key.values())


def map_enrichment_row(row: dict) -> dict:
    traditional_uses = merge_nested_sources(
        remove_empty_items(row.get("traditional_uses"), ("id", "title", "description"))
    )
    preparation_methods = merge_nested_sources(
        remove_empty_items(row.get("preparation_methods"), ("id", "title", "steps"))
    )
    usage_guidelines = merge_nested_sources(
        remove_empty_items(row.get("usage_guidelines"), ("id", "title", "description"))
    )
    safety_warnings = merge_nested_sources(
        remove_empty_items(row.get("safety_warnings"), ("id", "title", "description"))
    )
    clinical_guidelines = merge_nested_sources(
        remove_empty_items(row.get("clinical_guidelines"), ("id", "mechanism", "therapeutic_dose_text"))
    )
    claims = merge_nested_sources(remove_empty_items(row.get("claims"), ("claim_id", "claim_text", "evidence_summary")))

    for item in safety_warnings:
        item.setdefault("severity", "caution")
        item.setdefault("verification_status", "limited")

    mapped = {
        "traditional_uses": traditional_uses,
        "preparation_methods": _merge_list_field(preparation_methods, "formulations"),
        "usage_guidelines": usage_guidelines,
        "safety_warnings": _merge_list_field(safety_warnings, "population_risks"),
        "plant_parts": remove_empty_items(row.get("plant_parts"), ("id", "name")),
        "storage_guidelines": remove_empty_items(row.get("storage_guidelines"), ("id", "title", "description")),
        "myth_facts": remove_empty_items(row.get("myth_facts"), ("id", "claim", "fact")),
        "quality_standards": remove_empty_items(row.get("quality_standards"), ("id", "parameter", "value")),
        "clinical_guidelines": _merge_list_field(clinical_guidelines, "visible_to"),
        "drug_interactions": _merge_list_field(
            remove_empty_items(row.get("drug_interactions"), ("id", "substance", "description")), "population_risks"
        ),
        "contraindications": _merge_list_field(
            remove_empty_items(row.get("contraindications"), ("id", "condition", "description")), "population_risks"
        ),
        "pharmacokinetic_profiles": remove_empty_items(
            row.get("pharmacokinetic_profiles"), ("absorption", "distribution", "metabolism", "excretion")
        ),
        "research_topics": _merge_list_field(remove_empty_items(row.get("research_topics"), ("id", "title")), "visible_to"),
        "claims": claims,
        "related_symptoms": _merge_list_field(remove_empty_items(row.get("related_symptoms"), ("id", "name")), "aliases"),
    }
    return json_safe(mapped)


def filter_by_persona(enrichment: dict[str, Any], persona: str) -> dict[str, Any]:
    persona = persona or "umum"
    result = deepcopy(empty_enrichment() | (enrichment or {}))

    def visible(items: list[dict]) -> list[dict]:
        filtered = []
        for item in items or []:
            visible_to = item.get("visible_to") if isinstance(item, dict) else None
            if not visible_to or persona in visible_to:
                filtered.append(item)
        return filtered

    for key in ("clinical_guidelines", "research_topics"):
        result[key] = visible(result.get(key, []))

    if persona == "umum":
        safe_clinical = []
        for item in result.get("clinical_guidelines", []):
            cleaned = dict(item)
            if cleaned.get("therapeutic_dose_text"):
                cleaned["therapeutic_dose_text"] = None
                cleaned["notes"] = " ".join(filter(None, [cleaned.get("notes"), CLINICAL_DOSE_NOTICE]))
            safe_clinical.append(cleaned)
        result["clinical_guidelines"] = safe_clinical
        result["pharmacokinetic_profiles"] = []
        result["research_topics"] = []
        result["claims"] = []

    return json_safe(result)
