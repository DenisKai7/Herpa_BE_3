"""Retrieval audit data collection.

Hooks into the GraphRetriever to capture detailed diagnostics without
modifying production code. Wraps the retriever's retrieve() call and
inspects the result to build an audit record.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EntityAudit:
    """Audit of entity resolution for a single query."""
    detected_entities: list[str] = field(default_factory=list)
    detected_diseases: list[str] = field(default_factory=list)
    detected_compounds: list[str] = field(default_factory=list)
    detected_pharma_activity: list[str] = field(default_factory=list)
    detected_aliases: list[str] = field(default_factory=list)
    missing_entity: bool = False
    fallback_used: bool = False
    fallback_reason: str = ""


@dataclass
class RetrievalAudit:
    """Full audit record for a single retrieval operation."""
    # Entity resolution
    entity_audit: EntityAudit = field(default_factory=EntityAudit)

    # Neo4j execution
    cypher_queries: list[str] = field(default_factory=list)
    neo4j_execution_ms: float = 0.0

    # Candidate counts
    total_candidate_nodes: int = 0
    total_candidate_relations: int = 0

    # Retrieved IDs
    retrieved_node_ids: list[str] = field(default_factory=list)
    retrieved_relation_ids: list[str] = field(default_factory=list)

    # Final ranked
    final_ranked_nodes: list[dict[str, Any]] = field(default_factory=list)
    final_ranked_relations: list[dict[str, Any]] = field(default_factory=list)

    # Graph structure
    graph_depth: int = 0
    graph_breadth: int = 0

    # Warnings
    warnings: list[str] = field(default_factory=list)

    # Timing
    total_retrieval_ms: float = 0.0
    graph_expansion_ms: float = 0.0
    ranking_ms: float = 0.0

    # Previous query duplicate detection
    is_duplicate_of_previous: bool = False

    @classmethod
    def empty(cls, reason: str = "") -> "RetrievalAudit":
        """Create an empty audit record (e.g. when retrieval fails)."""
        return cls(
            warnings=[reason] if reason else ["Empty audit — retrieval failed"],
        )


# Known entity patterns for audit
_KNOWN_HERBS = {
    "kunyit": "Curcuma longa", "turmeric": "Curcuma longa",
    "jahe": "Zingiber officinale", "ginger": "Zingiber officinale",
    "temulawak": "Curcuma xanthorrhiza",
    "meniran": "Phyllanthus niruri",
    "pegagan": "Centella asiatica",
    "sambiloto": "Andrographis paniculata",
    "daun sirih": "Piper betle",
    "bawang putih": "Allium sativum",
    "lidah buaya": "Aloe vera",
    "mahkota dewa": "Phaleria macrocarpa",
    "mengkudu": "Morinda citrifolia",
    "kencur": "Kaempferia galanga",
    "asam jawa": "Tamarindus indica",
    "kemangi": "Ocimum basilicum",
    "jeruk nipis": "Citrus aurantifolia",
    "jambu biji": "Psidium guajava",
    "kelor": "Moringa oleifera",
    "kumis kucing": "Orthosiphon aristatus",
}

_KNOWN_COMPOUNDS = {
    "kurkumin": "curcumin", "curcumin": "curcumin",
    "gingerol": "gingerol", "shogaol": "shogaol",
    "andrografolida": "andrographolide", "andrographolide": "andrographolide",
    "asiaticoside": "asiaticoside", "madecassoside": "madecassoside",
    "allicin": "allicin",
    "quercetin": "quercetin",
    "flavonoid": "flavonoid", "flavonoid": "flavonoid",
    "tanin": "tannin", "tannin": "tannin",
    "saponin": "saponin",
    "terpenoid": "terpenoid",
    "alkaloid": "alkaloid",
}

_DISEASE_KEYWORDS = {
    "diabetes", "hipertensi", "kolesterol", "asma", "batuk",
    "demam", "malaria", "kanker", "tumor", "inflamasi",
    "asam urat", "rematik", "maag", "diare", "disentri",
    "anemia", "insomnia", "depresi", "stres", "alergi",
}

_PHARMA_ACTIVITY = {
    "antiinflamasi", "anti-inflamasi", "antioxidan", "antioksidan",
    "antimikroba", "antibakteri", "antivirus", "antijamur",
    "antipiretik", "analgesik", "hepatoprotektif", "neuroprotektif",
    "kardioprotektif", "antikanker", "antidiabetes", "antihipertensi",
    "diuretik", "laksatif", "sedatif", "tonik",
}


def _detect_entities_from_query(query: str) -> EntityAudit:
    """Detect entities from the query text using pattern matching."""
    audit = EntityAudit()
    query_lower = query.lower()

    # Detect herbs
    for local_name, scientific_name in _KNOWN_HERBS.items():
        if local_name in query_lower:
            audit.detected_entities.append(f"{local_name} ({scientific_name})")
            audit.detected_aliases.append(local_name)

    # Detect compounds
    for compound_key, compound_name in _KNOWN_COMPOUNDS.items():
        if compound_key in query_lower:
            audit.detected_compounds.append(compound_name)

    # Detect diseases
    for disease in _DISEASE_KEYWORDS:
        if disease in query_lower:
            audit.detected_diseases.append(disease)

    # Detect pharmacological activity
    for activity in _PHARMA_ACTIVITY:
        if activity in query_lower:
            audit.detected_pharma_activity.append(activity)

    # Check if entity was found
    if not audit.detected_entities and not audit.detected_compounds:
        audit.missing_entity = True
        audit.fallback_used = True
        audit.fallback_reason = "No known herb/compound entity detected in query"

    return audit


def _extract_node_ids_from_retrieval(retrieval: dict[str, Any]) -> list[str]:
    """Extract node identifiers from retrieval result."""
    ids = []
    for entity in retrieval.get("entities", []):
        eid = entity.get("entity_id") or entity.get("canonical_name") or entity.get("original_text", "")
        if eid:
            ids.append(str(eid))
    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        pid = plant.get("plant_id") or plant.get("id") or plant.get("scientific_name", "")
        if pid:
            ids.append(str(pid))
        for compound in fact.get("compounds", []):
            if isinstance(compound, dict):
                cid = compound.get("compound_id") or compound.get("id") or compound.get("name", "")
                if cid:
                    ids.append(str(cid))
    return ids


def _extract_relation_info(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract relation information from retrieval result."""
    relations = []
    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        plant_name = plant.get("scientific_name") or plant.get("local_name", "unknown")

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict):
                relations.append({
                    "type": "HAS_COMPOUND",
                    "source": plant_name,
                    "target": compound.get("name", "unknown"),
                })

        for use in fact.get("therapeutic_uses", []):
            if isinstance(use, dict):
                relations.append({
                    "type": "USED_FOR",
                    "source": plant_name,
                    "target": use.get("name", "unknown"),
                })

        for family in fact.get("families", []):
            if isinstance(family, dict):
                relations.append({
                    "type": "BELONGS_TO",
                    "source": plant_name,
                    "target": family.get("name", "unknown"),
                })

        for target in fact.get("protein_targets", []):
            if isinstance(target, dict):
                relations.append({
                    "type": "HAS_PROTEIN_TARGET",
                    "source": plant_name,
                    "target": target.get("name", "unknown"),
                })

        if fact.get("contraindications"):
            for contra in fact["contraindications"]:
                if isinstance(contra, dict):
                    relations.append({
                        "type": "HAS_CONTRAINDICATION",
                        "source": plant_name,
                        "target": contra.get("name", "unknown"),
                    })

        if fact.get("side_effects"):
            for se in fact["side_effects"]:
                if isinstance(se, dict):
                    relations.append({
                        "type": "HAS_SIDE_EFFECT",
                        "source": plant_name,
                        "target": se.get("name", "unknown"),
                    })

    return relations


def _build_ranked_nodes(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    """Build ranked node list from retrieval result."""
    ranked = []
    seen = set()

    for entity in retrieval.get("entities", []):
        name = entity.get("canonical_name") or entity.get("original_text", "")
        if name and name not in seen:
            ranked.append({
                "name": name,
                "type": entity.get("entity_type", "unknown"),
                "confidence": entity.get("confidence", 0.0),
                "rank": len(ranked) + 1,
            })
            seen.add(name)

    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        name = plant.get("scientific_name") or plant.get("local_name", "")
        if name and name not in seen:
            ranked.append({
                "name": name,
                "type": "herb",
                "confidence": 1.0,
                "rank": len(ranked) + 1,
            })
            seen.add(name)

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict):
                cname = compound.get("name", "")
                if cname and cname not in seen:
                    ranked.append({
                        "name": cname,
                        "type": "compound",
                        "confidence": 0.8,
                        "rank": len(ranked) + 1,
                    })
                    seen.add(cname)

    return ranked


def _check_duplicate(previous_audit: RetrievalAudit | None, current_audit: RetrievalAudit | None) -> bool:
    """Check if current retrieval is duplicate of previous.

    Defensive: both arguments may be None.
    """
    if previous_audit is None:
        return False
    if current_audit is None:
        return False
    prev_nodes = set(getattr(previous_audit, "retrieved_node_ids", []) or [])
    curr_nodes = set(getattr(current_audit, "retrieved_node_ids", []) or [])
    if not prev_nodes or not curr_nodes:
        return False
    overlap = len(prev_nodes & curr_nodes)
    return overlap / max(len(prev_nodes), len(curr_nodes)) > 0.8


def build_retrieval_audit(
    query: str,
    retrieval: dict[str, Any] | None,
    retrieval_latency_ms: float,
    previous_audit: RetrievalAudit | None = None,
) -> RetrievalAudit:
    """Build a complete retrieval audit from query and retrieval result.

    This is called after the retriever has already been invoked.
    It does NOT modify the retrieval process — only inspects results.

    NEVER returns None — always returns a valid RetrievalAudit.
    """
    # Defensive: if retrieval is None/empty, return empty audit
    if not retrieval or not isinstance(retrieval, dict):
        return RetrievalAudit(
            entity_audit=_detect_entities_from_query(query or ""),
            warnings=["Retrieval result is None or empty"],
        )

    t0 = time.perf_counter()

    # Entity audit
    entity_audit = _detect_entities_from_query(query or "")

    # Check if retriever used fallback
    grounding_status = retrieval.get("grounding_status", "")
    if grounding_status == "fallback" or grounding_status == "error":
        entity_audit.fallback_used = True
        entity_audit.fallback_reason = f"Retriever grounding status: {grounding_status}"

    # Node and relation extraction
    node_ids = _extract_node_ids_from_retrieval(retrieval)
    relations = _extract_relation_info(retrieval)
    ranked_nodes = _build_ranked_nodes(retrieval)

    # Graph structure estimation
    facts = retrieval.get("facts", []) or []
    graph_depth = 1 if facts else 0
    graph_breadth = len(node_ids)

    # Build relation IDs
    relation_ids = [f"{r['type']}:{r['source']}->{r['target']}" for r in relations]

    # Warnings
    warnings = []
    if entity_audit.missing_entity:
        warnings.append("Entity not found in query — retrieval may use fallback")
    if entity_audit.fallback_used:
        warnings.append(f"Fallback used: {entity_audit.fallback_reason}")
    if not facts:
        warnings.append("Graph expansion empty — no facts retrieved")
    if graph_breadth > 50:
        warnings.append(f"Graph expansion too large: {graph_breadth} nodes")

    build_ms = (time.perf_counter() - t0) * 1000

    # Build audit first, then check duplicate
    audit = RetrievalAudit(
        entity_audit=entity_audit,
        cypher_queries=[],
        neo4j_execution_ms=retrieval_latency_ms,
        total_candidate_nodes=len(node_ids),
        total_candidate_relations=len(relation_ids),
        retrieved_node_ids=node_ids,
        retrieved_relation_ids=relation_ids,
        final_ranked_nodes=ranked_nodes,
        final_ranked_relations=relations,
        graph_depth=graph_depth,
        graph_breadth=graph_breadth,
        warnings=warnings,
        total_retrieval_ms=retrieval_latency_ms,
        graph_expansion_ms=0.0,
        ranking_ms=0.0,
        is_duplicate_of_previous=False,
    )

    # Duplicate check (previous_audit may be None — handled inside)
    is_duplicate = _check_duplicate(previous_audit, audit)
    audit.is_duplicate_of_previous = is_duplicate

    if is_duplicate:
        audit.warnings.append("Duplicate of previous query retrieval — same nodes returned")

    return audit


def audit_to_dict(audit: RetrievalAudit | None) -> dict[str, Any]:
    """Convert RetrievalAudit to a plain dict for JSON serialization.

    Defensive: if audit is None, returns an empty dict.
    """
    if audit is None:
        return {
            "entity_audit": {},
            "cypher_queries": [],
            "retrieved_node_ids": [],
            "retrieved_relation_ids": [],
            "warnings": ["audit was None"],
        }
    ea = getattr(audit, "entity_audit", None)
    return {
        "entity_audit": {
            "detected_entities": getattr(ea, "detected_entities", []) if ea else [],
            "detected_diseases": getattr(ea, "detected_diseases", []) if ea else [],
            "detected_compounds": getattr(ea, "detected_compounds", []) if ea else [],
            "detected_pharma_activity": getattr(ea, "detected_pharma_activity", []) if ea else [],
            "detected_aliases": getattr(ea, "detected_aliases", []) if ea else [],
            "missing_entity": getattr(ea, "missing_entity", False) if ea else False,
            "fallback_used": getattr(ea, "fallback_used", False) if ea else False,
            "fallback_reason": getattr(ea, "fallback_reason", "") if ea else "",
        },
        "cypher_queries": getattr(audit, "cypher_queries", []),
        "neo4j_execution_ms": getattr(audit, "neo4j_execution_ms", 0.0),
        "total_candidate_nodes": getattr(audit, "total_candidate_nodes", 0),
        "total_candidate_relations": getattr(audit, "total_candidate_relations", 0),
        "retrieved_node_ids": getattr(audit, "retrieved_node_ids", []),
        "retrieved_relation_ids": getattr(audit, "retrieved_relation_ids", []),
        "final_ranked_nodes": getattr(audit, "final_ranked_nodes", []),
        "final_ranked_relations": getattr(audit, "final_ranked_relations", []),
        "graph_depth": getattr(audit, "graph_depth", 0),
        "graph_breadth": getattr(audit, "graph_breadth", 0),
        "warnings": getattr(audit, "warnings", []),
        "total_retrieval_ms": getattr(audit, "total_retrieval_ms", 0.0),
        "graph_expansion_ms": getattr(audit, "graph_expansion_ms", 0.0),
        "ranking_ms": getattr(audit, "ranking_ms", 0.0),
        "is_duplicate_of_previous": getattr(audit, "is_duplicate_of_previous", False),
    }
