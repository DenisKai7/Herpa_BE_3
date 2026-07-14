"""Evaluation-specific context builder.

Builds rich, structured context from GraphRAG retrieval results.
Only used in evaluation pipeline — does NOT modify production context_builder.

Key differences from production format_herb_fact:
  - Extracts ALL available fields from each node
  - Builds relation summaries
  - Ensures minimum context length when nodes > 0
  - Never returns empty context when retrieval succeeded
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Minimum context length target (chars)
MIN_CONTEXT_CHARS = 1000
# Separator between nodes
_NODE_SEP = "\n" + "=" * 50 + "\n"
# Separator between fields within a node
_FIELD_SEP = "\n"


def _safe_str(val: Any) -> str:
    """Convert value to string, return empty if None."""
    if val is None:
        return ""
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v)
    return str(val).strip()


def _extract_names(items: list[Any] | None) -> list[str]:
    """Extract names from a list of dicts or strings."""
    if not items:
        return []
    names = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("label") or item.get("term", "")
            if name:
                names.append(str(name))
        elif isinstance(item, str) and item:
            names.append(item)
    return names


def _format_node_from_fact(fact: dict[str, Any]) -> str:
    """Format a single fact (herb profile) into rich context text.

    Extracts ALL available fields, not just the ones production uses.
    """
    plant = fact.get("plant") or {}
    sections = []

    # Entity name
    local_name = _safe_str(plant.get("local_name"))
    scientific_name = _safe_str(plant.get("scientific_name"))
    latin_name = _safe_str(plant.get("latin_name"))
    simplisia_name = _safe_str(plant.get("simplisia_name"))

    entity_header = local_name or scientific_name or latin_name or "Unknown"
    sections.append(f"Entity: {entity_header}")

    if scientific_name:
        sections.append(f"Scientific Name: {scientific_name}")
    if latin_name and latin_name != scientific_name:
        sections.append(f"Latin Name: {latin_name}")
    if simplisia_name:
        sections.append(f"Simplisia Name: {simplisia_name}")

    # Status
    status = _safe_str(plant.get("status"))
    if status:
        sections.append(f"Status: {status}")

    # Descriptions
    for desc_key in ["description", "macroscopic_description", "microscopic_description"]:
        desc = _safe_str(plant.get(desc_key))
        if desc:
            label = desc_key.replace("_", " ").title()
            sections.append(f"{label}: {desc}")

    # Synonyms / local names
    synonyms = plant.get("synonyms") or plant.get("local_names") or []
    if synonyms:
        sections.append(f"Synonyms: {', '.join(str(s) for s in synonyms[:10])}")

    # Family
    families = _extract_names(fact.get("families"))
    if families:
        sections.append(f"Family: {', '.join(families[:5])}")

    # Compounds
    compounds = _extract_names(fact.get("compounds"))
    if compounds:
        sections.append(f"Compounds: {', '.join(compounds[:20])}")

    # Therapeutic uses
    uses = _extract_names(fact.get("therapeutic_uses") or fact.get("traditional_uses"))
    if uses:
        sections.append(f"Therapeutic Uses: {', '.join(uses[:20])}")

    # Benefits / indications
    benefits = _extract_names(fact.get("benefits") or fact.get("indications"))
    if benefits:
        sections.append(f"Benefits: {', '.join(benefits[:10])}")

    # Side effects
    side_effects = _extract_names(fact.get("side_effects"))
    if side_effects:
        sections.append(f"Side Effects: {', '.join(side_effects[:10])}")

    # Contraindications
    contraindications = _extract_names(fact.get("contraindications"))
    if contraindications:
        sections.append(f"Contraindications: {', '.join(contraindications[:10])}")

    # Drug interactions
    interactions = _extract_names(fact.get("interactions") or fact.get("drug_interactions"))
    if interactions:
        sections.append(f"Drug Interactions: {', '.join(interactions[:10])}")

    # Toxicity
    toxicity = _extract_names(fact.get("toxicity"))
    if toxicity:
        sections.append(f"Toxicity: {', '.join(toxicity[:5])}")

    # Protein targets
    targets = fact.get("protein_targets") or []
    if targets:
        target_strs = []
        for t in targets[:10]:
            if isinstance(t, dict):
                parts = [t.get("name"), t.get("mechanism"), t.get("affinity_range")]
                target_strs.append(" | ".join(str(p) for p in parts if p))
            elif isinstance(t, str):
                target_strs.append(t)
        if target_strs:
            sections.append(f"Protein Targets: {'; '.join(target_strs)}")

    # Sources / references
    sources = _extract_names(fact.get("sources") or fact.get("references"))
    if sources:
        sections.append(f"References: {', '.join(sources[:5])}")

    # Preparation / dosage
    preparation = _safe_str(fact.get("preparation") or fact.get("dosage"))
    if preparation:
        sections.append(f"Preparation/Dosage: {preparation}")

    # Part used
    part_used = _safe_str(fact.get("part_used") or fact.get("plant_part"))
    if part_used:
        sections.append(f"Part Used: {part_used}")

    return _FIELD_SEP.join(sections)


def _format_entity_context(entity: dict[str, Any]) -> str:
    """Format entity data into context when facts are sparse."""
    parts = []
    name = entity.get("canonical_name") or entity.get("original_text", "")
    etype = entity.get("entity_type", "unknown")
    confidence = entity.get("confidence", 0.0)

    if name:
        parts.append(f"Entity: {name}")
    if etype and etype != "unknown":
        parts.append(f"Type: {etype}")
    if confidence > 0:
        parts.append(f"Confidence: {confidence:.2f}")

    # Extra metadata
    for key in ["scientific_name", "local_name", "description", "category", "family"]:
        val = entity.get(key)
        if val:
            label = key.replace("_", " ").title()
            parts.append(f"{label}: {val}")

    return _FIELD_SEP.join(parts)


def _format_relation_summary(retrieval: dict[str, Any]) -> str:
    """Build a relation summary from retrieval facts."""
    relations = []
    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        plant_name = plant.get("scientific_name") or plant.get("local_name", "Unknown")

        for compound in (fact.get("compounds") or [])[:10]:
            if isinstance(compound, dict):
                cname = compound.get("name", "unknown")
                relations.append(f"{plant_name} HAS_COMPOUND {cname}")

        for use in (fact.get("therapeutic_uses") or fact.get("traditional_uses") or [])[:10]:
            if isinstance(use, dict):
                uname = use.get("name", "unknown")
                relations.append(f"{plant_name} USED_FOR {uname}")

        for target in (fact.get("protein_targets") or [])[:5]:
            if isinstance(target, dict):
                tname = target.get("name", "unknown")
                relations.append(f"{plant_name} ACTS_ON {tname}")

        for se in (fact.get("side_effects") or [])[:5]:
            if isinstance(se, dict):
                sename = se.get("name", "unknown")
                relations.append(f"{plant_name} HAS_SIDE_EFFECT {sename}")

        for contra in (fact.get("contraindications") or [])[:5]:
            if isinstance(contra, dict):
                cname = contra.get("name", "unknown")
                relations.append(f"{plant_name} HAS_CONTRAINDICATION {cname}")

    if not relations:
        return ""
    return "Relations:\n" + "\n".join(f"  - {r}" for r in relations[:30])


def build_evaluation_context(
    retrieval: dict[str, Any],
    query: str,
    max_chars: int = 4000,
) -> tuple[list[str], dict[str, Any]]:
    """Build rich evaluation context from retrieval result.

    Returns:
        (contexts, diagnostics) where contexts is a list of text chunks
        and diagnostics contains context building statistics.

    This function NEVER returns empty contexts when nodes > 0.
    """
    diagnostics = {
        "source": "none",
        "nodes_used": 0,
        "facts_used": 0,
        "chunks_built": 0,
        "total_chars": 0,
        "estimated_tokens": 0,
        "warnings": [],
    }

    if not retrieval or not isinstance(retrieval, dict):
        diagnostics["warnings"].append("Retrieval result is None or empty")
        return [], diagnostics

    raw_chunks: list[str] = []

    # ── Primary: Build from facts (full herb profiles) ──
    facts = retrieval.get("facts") or []
    for fact in facts:
        text = _format_node_from_fact(fact)
        if text.strip() and len(text.strip()) > 20:
            raw_chunks.append(text)

    if raw_chunks:
        diagnostics["source"] = "facts"
        diagnostics["facts_used"] = len(raw_chunks)

    # ── Add relation summary if we have facts ──
    if facts:
        rel_summary = _format_relation_summary(retrieval)
        if rel_summary:
            raw_chunks.append(rel_summary)

    # ── Fallback 1: Build from entities if facts are sparse ──
    entities = retrieval.get("entities") or []
    if len(raw_chunks) < 2 and entities:
        logger.info(f"Few facts ({len(raw_chunks)}), supplementing from {len(entities)} entities")
        for entity in entities:
            text = _format_entity_context(entity)
            if text.strip() and len(text.strip()) > 10:
                # Avoid duplicates with fact-based chunks
                entity_name = (entity.get("canonical_name") or entity.get("original_text", "")).lower()
                is_duplicate = any(entity_name in chunk.lower() for chunk in raw_chunks if entity_name)
                if not is_duplicate:
                    raw_chunks.append(text)
        if diagnostics["source"] == "none":
            diagnostics["source"] = "entities"

    # ── Fallback 2: Extract from ranked nodes if still sparse ──
    total_chars = sum(len(c) for c in raw_chunks)
    if total_chars < MIN_CONTEXT_CHARS:
        ranked_nodes = retrieval.get("final_ranked_nodes") or []
        if ranked_nodes:
            node_texts = []
            for node in ranked_nodes[:20]:
                name = node.get("name", "")
                ntype = node.get("type", "unknown")
                if name:
                    node_texts.append(f"Node: {name} (type: {ntype})")
            if node_texts:
                raw_chunks.append("Graph Nodes:\n" + "\n".join(node_texts))
                if diagnostics["source"] == "none":
                    diagnostics["source"] = "ranked_nodes"

    # ── Final safety: if still empty but we have entities/facts data ──
    if not raw_chunks:
        # Last resort: dump raw retrieval keys as context
        entity_count = len(entities)
        fact_count = len(facts)
        if entity_count > 0 or fact_count > 0:
            fallback = f"Retrieval found {entity_count} entities and {fact_count} facts. "
            fallback += f"Query: {query}"
            raw_chunks.append(fallback)
            diagnostics["source"] = "fallback_summary"
            diagnostics["warnings"].append("Used fallback summary — no rich context available")

    # ── Apply token budget ──
    result = _apply_token_budget(raw_chunks, max_chars)

    # ── Update diagnostics ──
    diagnostics["nodes_used"] = len(retrieval.get("entities") or [])
    diagnostics["chunks_built"] = len(result)
    diagnostics["total_chars"] = sum(len(c) for c in result)
    diagnostics["estimated_tokens"] = diagnostics["total_chars"] // 4

    # ── Validation ──
    if diagnostics["nodes_used"] > 0 and diagnostics["total_chars"] == 0:
        diagnostics["warnings"].append(
            f"BUG: nodes={diagnostics['nodes_used']} but context=0"
        )
    if diagnostics["total_chars"] < MIN_CONTEXT_CHARS and diagnostics["nodes_used"] > 0:
        diagnostics["warnings"].append(
            f"Context too short: {diagnostics['total_chars']} chars < {MIN_CONTEXT_CHARS} target"
        )

    return result, diagnostics


def _apply_token_budget(chunks: list[str], max_chars: int) -> list[str]:
    """Apply character budget to chunks, keeping the most informative ones."""
    if not chunks:
        return []

    # Sort by length (longer = more informative) but keep original order for ties
    scored = []
    for i, chunk in enumerate(chunks):
        # Score: length bonus + keyword density bonus
        score = len(chunk)
        # Bonus for chunks with structured data
        if ":" in chunk and "\n" in chunk:
            score += 100
        scored.append((score, i, chunk))

    # Sort by score descending
    scored.sort(key=lambda x: (-x[0], x[1]))

    result = []
    total_chars = 0

    for _score, _orig_idx, text in scored:
        if total_chars + len(text) <= max_chars:
            result.append(text)
            total_chars += len(text)
        else:
            # Try to fit a truncated version
            remaining = max_chars - total_chars
            if remaining > 100:  # At least 100 chars
                truncated = text[:remaining] + "..."
                result.append(truncated)
                total_chars += len(truncated)
            break

    # Restore original order
    original_order = []
    for chunk in chunks:
        if chunk in result:
            original_order.append(chunk)
    return original_order


def format_context_for_judge(contexts: list[str], max_chars: int = 2000) -> str:
    """Format contexts list into a single string for judge prompt.

    Uses separator between chunks for readability.
    """
    if not contexts:
        return ""

    combined = "\n---\n".join(contexts)
    if len(combined) > max_chars:
        combined = combined[:max_chars] + "..."
    return combined
