"""Graph Retrieval Accuracy: node and relationship precision/recall."""

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
            relationships.add("HAS_TOXICITY")

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
    """Compute graph retrieval accuracy for a single query."""
    retrieved_nodes = extract_nodes_from_retrieval(retrieval)
    retrieved_rels = extract_relationships_from_retrieval(retrieval)

    node_metrics = compute_node_metrics(retrieved_nodes, expected_nodes)
    rel_metrics = compute_relationship_metrics(retrieved_rels, expected_relationships)

    # Overall accuracy: average of all four metrics
    overall = (
        node_metrics["precision"]
        + node_metrics["recall"]
        + rel_metrics["precision"]
        + rel_metrics["recall"]
    ) / 4

    return {
        "node_precision": node_metrics["precision"],
        "node_recall": node_metrics["recall"],
        "relationship_precision": rel_metrics["precision"],
        "relationship_recall": rel_metrics["recall"],
        "overall_accuracy": round(overall, 4),
        "retrieved_nodes": list(retrieved_nodes),
        "retrieved_relationships": list(retrieved_rels),
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

    return aggregated
