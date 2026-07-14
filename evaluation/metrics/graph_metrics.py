"""Graph Retrieval Accuracy: node and relationship precision/recall.

Enhanced with detailed node/relation tracking, IDs, and graph structure info.
"""

from typing import Any


def extract_nodes_from_retrieval(retrieval: dict[str, Any]) -> set[str]:
    """Extract node names from retrieval result."""
    nodes = set()

    for entity in retrieval.get("entities", []):
        if entity.get("canonical_name"):
            nodes.add(entity["canonical_name"].lower())
        if entity.get("original_text"):
            nodes.add(entity["original_text"].lower())

    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        if plant.get("local_name"):
            nodes.add(plant["local_name"].lower())
        if plant.get("scientific_name"):
            nodes.add(plant["scientific_name"].lower())

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict) and compound.get("name"):
                nodes.add(compound["name"].lower())

        for use in fact.get("therapeutic_uses", []):
            if isinstance(use, dict) and use.get("name"):
                nodes.add(use["name"].lower())

        for target in fact.get("protein_targets", []):
            if isinstance(target, dict) and target.get("name"):
                nodes.add(target["name"].lower())

    return nodes


def extract_relationships_from_retrieval(retrieval: dict[str, Any]) -> set[str]:
    """Extract relationship types from retrieval result."""
    relationships = set()

    for fact in retrieval.get("facts", []):
        if fact.get("compounds"):
            relationships.add("HAS_COMPOUND")
        if fact.get("therapeutic_uses"):
            relationships.add("USED_FOR")
        if fact.get("families"):
            relationships.add("BELONGS_TO")
        if fact.get("protein_targets"):
            relationships.add("HAS_PROTEIN_TARGET")
        if fact.get("toxicity"):
            relationships.add("HAS_TOXICITY")
        if fact.get("sources"):
            relationships.add("VERIFIED_BY")
        if fact.get("contraindications"):
            relationships.add("HAS_CONTRAINDICATION")
        if fact.get("side_effects"):
            relationships.add("HAS_SIDE_EFFECT")

    return relationships


def extract_detailed_nodes(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract detailed node information for audit."""
    nodes = []
    seen = set()

    for entity in retrieval.get("entities", []):
        name = entity.get("canonical_name") or entity.get("original_text", "")
        if name and name.lower() not in seen:
            nodes.append({
                "name": name,
                "type": entity.get("entity_type", "unknown"),
                "confidence": entity.get("confidence", 0.0),
                "source": "entity_resolution",
            })
            seen.add(name.lower())

    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        name = plant.get("scientific_name") or plant.get("local_name", "")
        if name and name.lower() not in seen:
            nodes.append({
                "name": name,
                "type": "herb",
                "confidence": 1.0,
                "source": "graph_retrieval",
                "local_name": plant.get("local_name", ""),
                "scientific_name": plant.get("scientific_name", ""),
            })
            seen.add(name.lower())

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict):
                cname = compound.get("name", "")
                if cname and cname.lower() not in seen:
                    nodes.append({
                        "name": cname,
                        "type": "compound",
                        "confidence": 0.8,
                        "source": "graph_retrieval",
                    })
                    seen.add(cname.lower())

        for use in fact.get("therapeutic_uses", []):
            if isinstance(use, dict):
                uname = use.get("name", "")
                if uname and uname.lower() not in seen:
                    nodes.append({
                        "name": uname,
                        "type": "therapeutic_use",
                        "confidence": 0.8,
                        "source": "graph_retrieval",
                    })
                    seen.add(uname.lower())

    return nodes


def extract_detailed_relationships(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract detailed relationship information for audit."""
    relationships = []

    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        plant_name = plant.get("scientific_name") or plant.get("local_name", "unknown")

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict):
                relationships.append({
                    "type": "HAS_COMPOUND",
                    "source": plant_name,
                    "target": compound.get("name", "unknown"),
                    "source_type": "herb",
                    "target_type": "compound",
                })

        for use in fact.get("therapeutic_uses", []):
            if isinstance(use, dict):
                relationships.append({
                    "type": "USED_FOR",
                    "source": plant_name,
                    "target": use.get("name", "unknown"),
                    "source_type": "herb",
                    "target_type": "therapeutic_use",
                })

        for family in fact.get("families", []):
            if isinstance(family, dict):
                relationships.append({
                    "type": "BELONGS_TO",
                    "source": plant_name,
                    "target": family.get("name", "unknown"),
                    "source_type": "herb",
                    "target_type": "family",
                })

        for target in fact.get("protein_targets", []):
            if isinstance(target, dict):
                relationships.append({
                    "type": "HAS_PROTEIN_TARGET",
                    "source": plant_name,
                    "target": target.get("name", "unknown"),
                    "source_type": "herb",
                    "target_type": "protein_target",
                })

        if fact.get("contraindications"):
            for contra in fact["contraindications"]:
                if isinstance(contra, dict):
                    relationships.append({
                        "type": "HAS_CONTRAINDICATION",
                        "source": plant_name,
                        "target": contra.get("name", "unknown"),
                        "source_type": "herb",
                        "target_type": "contraindication",
                    })

        if fact.get("side_effects"):
            for se in fact["side_effects"]:
                if isinstance(se, dict):
                    relationships.append({
                        "type": "HAS_SIDE_EFFECT",
                        "source": plant_name,
                        "target": se.get("name", "unknown"),
                        "source_type": "herb",
                        "target_type": "side_effect",
                    })

    return relationships


def compute_node_metrics(
    retrieved_nodes: set[str],
    expected_nodes: list[str],
) -> dict[str, float]:
    """Compute node precision and recall."""
    if not expected_nodes:
        return {"precision": 1.0, "recall": 1.0}

    expected_normalized = {n.lower() for n in expected_nodes}

    # Fuzzy matching: check if expected node is contained in retrieved or vice versa
    matched = set()
    for expected in expected_normalized:
        for retrieved in retrieved_nodes:
            if expected in retrieved or retrieved in expected:
                matched.add(expected)
                break

    precision = len(matched) / len(retrieved_nodes) if retrieved_nodes else 0.0
    recall = len(matched) / len(expected_normalized) if expected_normalized else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def compute_relationship_metrics(
    retrieved_rels: set[str],
    expected_rels: list[str],
) -> dict[str, float]:
    """Compute relationship precision and recall."""
    if not expected_rels:
        return {"precision": 1.0, "recall": 1.0}

    expected_normalized = {r.upper() for r in expected_rels}

    matched = retrieved_rels & expected_normalized

    precision = len(matched) / len(retrieved_rels) if retrieved_rels else 0.0
    recall = len(matched) / len(expected_normalized) if expected_normalized else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
    }


def compute_graph_accuracy(
    retrieval: dict[str, Any],
    expected_nodes: list[str],
    expected_relationships: list[str],
) -> dict[str, Any]:
    """Compute graph retrieval accuracy for a single query.

    Enhanced with detailed node/relation tracking and graph structure info.
    """
    retrieved_nodes = extract_nodes_from_retrieval(retrieval)
    retrieved_rels = extract_relationships_from_retrieval(retrieval)
    detailed_nodes = extract_detailed_nodes(retrieval)
    detailed_rels = extract_detailed_relationships(retrieval)

    node_metrics = compute_node_metrics(retrieved_nodes, expected_nodes)
    rel_metrics = compute_relationship_metrics(retrieved_rels, expected_relationships)

    # Overall accuracy: average of all four metrics
    overall = (
        node_metrics["precision"]
        + node_metrics["recall"]
        + rel_metrics["precision"]
        + rel_metrics["recall"]
    ) / 4

    # Graph structure
    graph_depth = 1 if retrieval.get("facts") else 0
    graph_breadth = len(retrieved_nodes)

    return {
        "node_precision": node_metrics["precision"],
        "node_recall": node_metrics["recall"],
        "relationship_precision": rel_metrics["precision"],
        "relationship_recall": rel_metrics["recall"],
        "overall_accuracy": round(overall, 4),
        "retrieved_nodes": list(retrieved_nodes),
        "retrieved_relationships": list(retrieved_rels),
        # Enhanced detail
        "detailed_nodes": detailed_nodes,
        "detailed_relationships": detailed_rels,
        "graph_depth": graph_depth,
        "graph_breadth": graph_breadth,
        "total_nodes": len(detailed_nodes),
        "total_relationships": len(detailed_rels),
    }


def aggregate_graph_metrics(all_results: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate graph metrics across all queries."""
    if not all_results:
        return {
            "node_precision": 0.0,
            "node_recall": 0.0,
            "relationship_precision": 0.0,
            "relationship_recall": 0.0,
            "overall_accuracy": 0.0,
        }

    keys = ["node_precision", "node_recall", "relationship_precision", "relationship_recall", "overall_accuracy"]
    aggregated = {}

    for key in keys:
        values = [r[key] for r in all_results if key in r]
        aggregated[key] = round(sum(values) / len(values), 4) if values else 0.0

    # Average graph structure
    depths = [r.get("graph_depth", 0) for r in all_results]
    breadths = [r.get("graph_breadth", 0) for r in all_results]
    aggregated["average_graph_depth"] = round(sum(depths) / len(depths), 2) if depths else 0
    aggregated["average_graph_breadth"] = round(sum(breadths) / len(breadths), 2) if breadths else 0

    return aggregated
