"""Citation accuracy: verify citations in answers match retrieved graph nodes."""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def extract_citations_from_answer(answer: str) -> list[str]:
    """Extract cited sources from LLM answer.

    Looks for patterns like [1], [2], (Sumber: ...), etc.
    Also extracts herb/compound names mentioned as sources.
    """
    citations = []

    # Pattern 1: Numbered references [1], [2], etc.
    numbered = re.findall(r'\[(\d+)\]', answer)
    citations.extend([f"[{n}]" for n in numbered])

    # Pattern 2: Source references (Sumber: ...) or (Ref: ...)
    source_refs = re.findall(r'\((?:Sumber|Ref|Referensi):\s*([^)]+)\)', answer, re.IGNORECASE)
    citations.extend(source_refs)

    # Pattern 3: Named entities that could be citations (herb names, scientific names)
    # Extract quoted terms
    quoted = re.findall(r'"([^"]+)"', answer)
    citations.extend(quoted)

    return citations


def extract_graph_nodes_from_retrieval(retrieval: dict[str, Any]) -> set[str]:
    """Extract all node names from retrieval result for citation verification."""
    nodes = set()

    # From entities
    for entity in retrieval.get("entities", []):
        if entity.get("canonical_name"):
            nodes.add(entity["canonical_name"].lower())
        if entity.get("original_text"):
            nodes.add(entity["original_text"].lower())

    # From facts
    for fact in retrieval.get("facts", []):
        plant = fact.get("plant", {})
        if plant.get("local_name"):
            nodes.add(plant["local_name"].lower())
        if plant.get("scientific_name"):
            nodes.add(plant["scientific_name"].lower())

        for compound in fact.get("compounds", []):
            if isinstance(compound, dict) and compound.get("name"):
                nodes.add(compound["name"].lower())

        for source in fact.get("sources", []):
            if isinstance(source, dict) and source.get("name"):
                nodes.add(source["name"].lower())

    return nodes


def verify_citation(
    citation: str,
    graph_nodes: set[str],
    contexts: list[str],
) -> dict[str, Any]:
    """Verify a single citation against graph nodes and contexts."""
    citation_lower = citation.lower().strip()

    # Check if citation matches a graph node
    for node in graph_nodes:
        if citation_lower in node or node in citation_lower:
            return {
                "citation": citation,
                "status": "correct",
                "matched_node": node,
                "reason": "Matches graph node",
            }

    # Check if citation appears in retrieved context
    combined_context = " ".join(contexts).lower()
    if citation_lower in combined_context:
        return {
            "citation": citation,
            "status": "correct",
            "matched_node": None,
            "reason": "Found in retrieved context",
        }

    # Check for partial matches (at least 60% of words match)
    citation_words = set(citation_lower.split())
    if len(citation_words) >= 2:
        for node in graph_nodes:
            node_words = set(node.split())
            overlap = citation_words & node_words
            if len(overlap) / len(citation_words) >= 0.6:
                return {
                    "citation": citation,
                    "status": "correct",
                    "matched_node": node,
                    "reason": f"Partial match ({len(overlap)}/{len(citation_words)} words)",
                }

    return {
        "citation": citation,
        "status": "incorrect",
        "matched_node": None,
        "reason": "No matching graph node or context found",
    }


def compute_citation_accuracy(
    answer: str,
    retrieval: dict[str, Any],
    contexts: list[str],
) -> dict[str, Any]:
    """Compute citation accuracy for a single query.

    Returns correct_count, incorrect_count, missing_count, accuracy, and details.
    """
    if not answer:
        return {
            "correct": 0,
            "incorrect": 0,
            "missing": 0,
            "accuracy": 0.0,
            "details": [],
        }

    citations = extract_citations_from_answer(answer)
    graph_nodes = extract_graph_nodes_from_retrieval(retrieval)

    if not citations:
        # No explicit citations found — check if answer mentions graph entities
        # This is common in the HERPA system where answers reference herbs directly
        mentioned_herbs = []
        for node in graph_nodes:
            if node in answer.lower():
                mentioned_herbs.append(node)

        if mentioned_herbs:
            return {
                "correct": len(mentioned_herbs),
                "incorrect": 0,
                "missing": 0,
                "accuracy": 1.0,
                "details": [
                    {"citation": h, "status": "correct", "reason": "Entity mentioned in answer"}
                    for h in mentioned_herbs
                ],
            }

        return {
            "correct": 0,
            "incorrect": 0,
            "missing": 0,
            "accuracy": 1.0,  # No citations to verify — treat as perfect
            "details": [],
        }

    details = []
    correct = 0
    incorrect = 0

    for citation in citations:
        result = verify_citation(citation, graph_nodes, contexts)
        details.append(result)
        if result["status"] == "correct":
            correct += 1
        else:
            incorrect += 1

    total = correct + incorrect
    accuracy = correct / total if total > 0 else 1.0

    return {
        "correct": correct,
        "incorrect": incorrect,
        "missing": 0,
        "accuracy": round(accuracy, 4),
        "details": details,
    }


def aggregate_citation_metrics(all_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate citation metrics across all queries."""
    if not all_results:
        return {"total_correct": 0, "total_incorrect": 0, "accuracy": 0.0}

    total_correct = sum(r.get("correct", 0) for r in all_results)
    total_incorrect = sum(r.get("incorrect", 0) for r in all_results)
    total = total_correct + total_incorrect

    return {
        "total_correct": total_correct,
        "total_incorrect": total_incorrect,
        "accuracy": round(total_correct / total, 4) if total > 0 else 1.0,
    }
