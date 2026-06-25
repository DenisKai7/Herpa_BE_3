"""
Herbal detail service — merges Knowledge Graph data with curated fallback profiles.

This service builds the complete herbal detail response for the detail drawer,
ensuring every section has meaningful content when available.
"""

from __future__ import annotations

import logging
from typing import Any

from app.data.curated_herbal_profiles import get_curated_profile
from app.graph.repositories import KnowledgeGraphRepository
from app.services.recommendation.enrichment_mapper import (
    dedupe_by_key,
    empty_enrichment,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Placeholder detection
# ---------------------------------------------------------------------------

_PLACEHOLDER_PATTERNS = [
    "belum tersedia",
    "informasi belum tersedia",
    "data belum tersedia",
    "tidak tersedia",
    "not available",
    "placeholder",
]


def is_placeholder_text(value: str | None, herb_name: str = "") -> bool:
    """Return True if *value* is empty or looks like a generic placeholder."""
    if not value:
        return True
    text = value.lower().strip()
    if not text:
        return True
    for pattern in _PLACEHOLDER_PATTERNS:
        if pattern in text:
            return True
    herb_lower = herb_name.lower().strip()
    if herb_lower:
        # Detect template-like strings: "Cara pengolahan tradisional Kunyit"
        if text == f"cara pengolahan tradisional {herb_lower}":
            return True
        if text == f"aturan pakai edukatif {herb_lower}":
            return True
    return False


def _has_text(value: Any) -> bool:
    """Check if a value contains meaningful non-placeholder text."""
    if value is None:
        return False
    if isinstance(value, str):
        return not is_placeholder_text(value)
    if isinstance(value, list):
        return any(_has_text(v) for v in value)
    if isinstance(value, dict):
        return any(_has_text(v) for v in value.values())
    return True


# ---------------------------------------------------------------------------
# Section-level helpers
# ---------------------------------------------------------------------------

def _is_section_empty(items: list[dict] | None, herb_name: str = "") -> bool:
    """Return True if a list-of-dicts section has no meaningful content."""
    if not items:
        return True
    for item in items:
        if not isinstance(item, dict):
            continue
        # Check for any field with meaningful text
        for key in ("title", "description", "name", "claim_text", "fact", "mechanism"):
            val = item.get(key)
            if val and not is_placeholder_text(str(val), herb_name):
                return False
        # Check array fields
        for key in ("steps", "ingredients", "morphology", "organoleptic"):
            arr = item.get(key)
            if isinstance(arr, list) and any(str(v).strip() for v in arr):
                return False
    return True


def _merge_list(
    kg_items: list[dict] | None,
    curated_items: list[dict] | None,
    herb_name: str = "",
) -> list[dict]:
    """Merge KG and curated lists: KG takes priority, curated fills gaps."""
    result: list[dict] = []

    # Add meaningful KG items
    for item in kg_items or []:
        if not isinstance(item, dict):
            continue
        # Skip if only title with no real content
        title = item.get("title") or item.get("name") or ""
        desc = item.get("description") or ""
        has_steps = bool(item.get("steps"))
        has_ingredients = bool(item.get("ingredients"))
        has_content = desc and not is_placeholder_text(desc, herb_name)
        if title and not has_content and not has_steps and not has_ingredients:
            # Title-only item — skip if it's a placeholder
            if is_placeholder_text(title, herb_name):
                continue
        result.append(item)

    # If KG had nothing meaningful, use curated
    if not result and curated_items:
        result = list(curated_items)

    return result


# ---------------------------------------------------------------------------
# Main detail builder
# ---------------------------------------------------------------------------

async def build_herb_detail(
    repository: KnowledgeGraphRepository,
    herb_id: str,
    *,
    common_name: str | None = None,
    scientific_name: str | None = None,
    family: str | None = None,
) -> dict[str, Any]:
    """Build complete herbal detail from KG + curated fallback.

    Returns a dict matching the target detail schema for the frontend drawer.
    """
    # 1. Fetch KG enrichment data
    kg_detail: dict[str, Any] = empty_enrichment()
    try:
        kg_detail = await repository.get_herb_detail_core(herb_id)
    except Exception:
        logger.exception("herbal_detail_kg_fetch_failed", extra={"herb_id": herb_id})

    # Also fetch basic herb info from KG
    kg_basic: dict[str, Any] | None = None
    try:
        kg_basic = await repository.get_herb_basic(herb_id)
    except Exception:
        logger.exception("herbal_detail_basic_fetch_failed", extra={"herb_id": herb_id})

    # Resolve herb identity
    resolved_common_name = (
        common_name
        or (kg_basic or {}).get("common_name")
        or (kg_basic or {}).get("commonName")
        or kg_detail.get("common_name")
        or ""
    )
    resolved_scientific_name = (
        scientific_name
        or (kg_basic or {}).get("scientific_name")
        or (kg_basic or {}).get("canonicalScientificName")
        or (kg_basic or {}).get("latinName")
        or kg_detail.get("scientific_name")
        or ""
    )
    resolved_family = family or ""

    # 2. Try curated profile by common name
    curated = get_curated_profile(resolved_common_name)

    # 3. Build botanical description
    botanical_description = _build_botanical_description(kg_detail, curated, resolved_common_name)

    # 4. Build plant parts
    plant_parts = _build_plant_parts(kg_detail, curated)

    # 5. Build each section with fallback
    traditional_uses = _merge_list(
        kg_detail.get("traditional_uses"),
        (curated or {}).get("traditional_uses"),
        resolved_common_name,
    )
    preparation_methods = _merge_list(
        kg_detail.get("preparation_methods"),
        (curated or {}).get("preparation_methods"),
        resolved_common_name,
    )
    usage_guidelines = _merge_list(
        kg_detail.get("usage_guidelines"),
        (curated or {}).get("usage_guidelines"),
        resolved_common_name,
    )
    safety_warnings = _merge_list(
        kg_detail.get("safety_warnings"),
        (curated or {}).get("safety_warnings"),
        resolved_common_name,
    )
    clinical_guidelines = _merge_list(
        kg_detail.get("clinical_guidelines"),
        [],  # No curated clinical — use safe defaults
        resolved_common_name,
    )
    # Ensure clinical has safe defaults
    clinical_guidelines = _ensure_clinical_safety(clinical_guidelines)

    claims = _merge_list(
        kg_detail.get("claims"),
        (curated or {}).get("claims"),
        resolved_common_name,
    )
    research_topics = _merge_list(
        kg_detail.get("research_topics"),
        (curated or {}).get("research_topics"),
        resolved_common_name,
    )
    sources = _build_sources(kg_detail, curated)
    drug_interactions = _merge_list(
        kg_detail.get("drug_interactions"),
        [],
        resolved_common_name,
    )
    contraindications = _merge_list(
        kg_detail.get("contraindications"),
        [],
        resolved_common_name,
    )
    related_symptoms = _build_related_symptoms(kg_detail)

    # 6. Data quality metadata
    has_kg = _has_kg_data(kg_detail)
    has_curated = curated is not None
    missing = _find_missing_sections(kg_detail, resolved_common_name)

    source_label = "knowledge_graph" if has_kg else ("curated_fallback" if has_curated else "none")
    if has_kg and has_curated and missing:
        source_label = "mixed"

    # 7. Log
    logger.info({
        "event": "herbal_detail_built",
        "herb_id": herb_id,
        "common_name": resolved_common_name,
        "kg_sections": {
            "botanical_description": bool(kg_detail.get("botanical_description")),
            "traditional_uses": len(kg_detail.get("traditional_uses") or []),
            "preparation_methods": len(kg_detail.get("preparation_methods") or []),
            "usage_guidelines": len(kg_detail.get("usage_guidelines") or []),
            "clinical_guidelines": len(kg_detail.get("clinical_guidelines") or []),
            "sources": len(kg_detail.get("sources") or []),
            "claims": len(kg_detail.get("claims") or []),
            "research_topics": len(kg_detail.get("research_topics") or []),
        },
        "fallback_sections_used": missing,
        "curated_profile_found": has_curated,
    })

    return {
        "herb_id": herb_id,
        "common_name": resolved_common_name,
        "scientific_name": resolved_scientific_name,
        "family": resolved_family,
        "plant_parts": plant_parts,
        "botanical_description": botanical_description,
        "traditional_uses": traditional_uses,
        "preparation_methods": preparation_methods,
        "usage_guidelines": usage_guidelines,
        "clinical_guidelines": clinical_guidelines,
        "safety_warnings": safety_warnings,
        "drug_interactions": drug_interactions,
        "contraindications": contraindications,
        "sources": sources,
        "claims": claims,
        "research_topics": research_topics,
        "related_symptoms": related_symptoms,
        "data_quality": {
            "source": source_label,
            "has_kg_data": has_kg,
            "has_curated_fallback": has_curated,
            "missing_sections": missing,
            "disclaimer": "Informasi bersifat edukatif dan tidak menggantikan konsultasi tenaga kesehatan.",
        },
    }


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_botanical_description(
    kg: dict[str, Any],
    curated: dict[str, Any] | None,
    herb_name: str,
) -> dict[str, Any]:
    """Build botanical description from KG or curated fallback."""
    # Check if KG has botanical_description
    kg_bd = kg.get("botanical_description")
    if isinstance(kg_bd, dict) and not is_placeholder_text(kg_bd.get("summary"), herb_name):
        return kg_bd

    # Try to construct from KG plant_parts + related data
    kg_summary_parts: list[str] = []
    plant_parts = kg.get("plant_parts")
    if isinstance(plant_parts, list):
        for part in plant_parts:
            if isinstance(part, dict):
                name = part.get("name") or ""
                desc = part.get("description") or ""
                if name:
                    kg_summary_parts.append(name)

    # Use curated if KG has nothing meaningful
    if curated:
        cbd = curated.get("botanical_description", {})
        if isinstance(cbd, dict) and cbd.get("summary"):
            return cbd

    # Minimal fallback
    if kg_summary_parts:
        return {
            "summary": f"{herb_name} — bagian yang digunakan: {', '.join(kg_summary_parts)}.",
            "morphology": [],
            "organoleptic": [],
        }

    return {
        "summary": f"Deskripsi botani untuk {herb_name} belum tersedia secara lengkap pada knowledge graph.",
        "morphology": [],
        "organoleptic": [],
    }


def _build_plant_parts(kg: dict[str, Any], curated: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Build plant parts list, preferring KG data."""
    parts = kg.get("plant_parts") or []
    if parts and any(isinstance(p, dict) and p.get("name") for p in parts):
        return [p for p in parts if isinstance(p, dict)]
    if curated:
        curated_parts = curated.get("plant_parts") or []
        if curated_parts and isinstance(curated_parts[0], str):
            return [{"name": p, "description": f"Bagian {p.lower()} digunakan secara tradisional."} for p in curated_parts]
        return curated_parts
    return []


def _build_sources(kg: dict[str, Any], curated: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Build sources list from KG and/or curated."""
    sources: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in kg.get("sources") or []:
        if not isinstance(source, dict):
            continue
        key = str(source.get("title") or source.get("source_id") or "")
        if key and key not in seen:
            seen.add(key)
            sources.append(source)

    # Add curated source if KG sources are empty or we have curated data
    if curated:
        curated_sources = curated.get("sources") or []
        for source in curated_sources:
            if not isinstance(source, dict):
                continue
            key = str(source.get("title") or "")
            if key and key not in seen:
                seen.add(key)
                sources.append(source)

    return sources


def _build_related_symptoms(kg: dict[str, Any]) -> list[dict[str, Any]]:
    """Build related symptoms from KG data."""
    raw = kg.get("related_symptoms") or []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict) and item.get("name"):
            result.append(item)
    return result


def _ensure_clinical_safety(items: list[dict]) -> list[dict]:
    """Ensure clinical guidelines have safe disclaimers."""
    result: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        cleaned = dict(item)
        # If there's a dose text, add safety note
        if cleaned.get("therapeutic_dose_text"):
            existing_notes = cleaned.get("notes") or ""
            safety_note = (
                "Dosis klinis belum tersedia/terverifikasi. "
                "Gunakan sebagai edukasi, bukan pengganti saran tenaga kesehatan."
            )
            cleaned["notes"] = f"{existing_notes} {safety_note}".strip() if existing_notes else safety_note
        result.append(cleaned)

    # If no clinical guidelines at all, add a safe placeholder
    if not result:
        result.append({
            "mechanism": "Belum tersedia panduan klinis spesifik pada knowledge graph.",
            "therapeutic_dose_text": None,
            "notes": (
                "Dosis klinis belum tersedia/terverifikasi. "
                "Gunakan sebagai edukasi, bukan pengganti saran tenaga kesehatan."
            ),
        })
    return result


def _has_kg_data(kg: dict[str, Any]) -> bool:
    """Check if KG returned any meaningful data."""
    for key in ("traditional_uses", "preparation_methods", "usage_guidelines", "safety_warnings", "claims"):
        items = kg.get(key)
        if items and any(isinstance(i, dict) for i in items):
            return True
    return False


def _find_missing_sections(kg: dict[str, Any], herb_name: str) -> list[str]:
    """Find which sections are missing or placeholder in KG data."""
    missing: list[str] = []
    check_keys = [
        ("botanical_description", "botanical_description"),
        ("traditional_uses", "traditional_uses"),
        ("preparation_methods", "preparation_methods"),
        ("usage_guidelines", "usage_guidelines"),
        ("safety_warnings", "safety_warnings"),
        ("sources", "sources"),
        ("claims", "claims"),
        ("research_topics", "research_topics"),
    ]
    for label, key in check_keys:
        val = kg.get(key)
        if key == "botanical_description":
            if not isinstance(val, dict) or is_placeholder_text(val.get("summary"), herb_name):
                missing.append(label)
        else:
            if _is_section_empty(val, herb_name):
                missing.append(label)
    return missing
