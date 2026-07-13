"""Retrieval evaluation metrics: Precision@k, Recall@k, Hit Rate@k, MRR, nDCG."""

import math
from typing import Any


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Precision@k = |retrieved in top-k ∩ relevant| / k."""
    if k <= 0:
        return 0.0
    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for item in retrieved_k if item in relevant_set)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Recall@k = |retrieved in top-k ∩ relevant| / |relevant|."""
    if not relevant:
        return 0.0
    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for item in retrieved_k if item in relevant_set)
    return hits / len(relevant_set)


def hit_rate_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Hit Rate@k = 1 if any relevant item in top-k, else 0."""
    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)
    return 1.0 if any(item in relevant_set for item in retrieved_k) else 0.0


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    """Mean Reciprocal Rank = 1 / rank of first relevant item."""
    relevant_set = set(relevant)
    for i, item in enumerate(retrieved):
        if item in relevant_set:
            return 1.0 / (i + 1)
    return 0.0


def ndcg(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain @k.

    DCG = sum(rel_i / log2(i+2)) for i in 0..k-1
    IDCG = sum(1 / log2(i+2)) for i in 0..min(k, |relevant|)-1
    nDCG = DCG / IDCG
    """
    if k <= 0 or not relevant:
        return 0.0

    relevant_set = set(relevant)
    retrieved_k = retrieved[:k]

    # DCG
    dcg = 0.0
    for i, item in enumerate(retrieved_k):
        rel = 1.0 if item in relevant_set else 0.0
        dcg += rel / math.log2(i + 2)

    # IDCG (ideal: all relevant items at top)
    ideal_count = min(len(relevant_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))

    return dcg / idcg if idcg > 0 else 0.0


def compute_retrieval_metrics(
    retrieved_items: list[str],
    ground_truth_nodes: list[str],
    ground_truth_facts: list[str],
) -> dict[str, Any]:
    """Compute all retrieval metrics for a single query.

    Uses ground_truth_facts as the relevant set for semantic matching,
    and ground_truth_nodes for node-level matching.
    Combines both for comprehensive evaluation.
    """
    # Combine ground truth: match against both node names and key facts
    relevant = list(set(ground_truth_nodes + ground_truth_facts))

    # Also do fuzzy matching: check if retrieved item contains any relevant term
    def fuzzy_match(retrieved_item: str, relevant_items: list[str]) -> bool:
        item_lower = retrieved_item.lower()
        return any(term.lower() in item_lower for term in relevant_items if len(term) >= 3)

    # For fuzzy matching, create a broader relevant set
    retrieved_normalized = retrieved_items
    relevant_normalized = relevant

    metrics = {}
    for k in [1, 3, 5]:
        metrics[f"precision@{k}"] = precision_at_k(retrieved_normalized, relevant_normalized, k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_normalized, relevant_normalized, k)
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_normalized, relevant_normalized, k)

    metrics["mrr"] = mrr(retrieved_normalized, relevant_normalized)
    metrics["ndcg"] = ndcg(retrieved_normalized, relevant_normalized, k=5)

    return metrics


def aggregate_retrieval_metrics(all_metrics: list[dict[str, Any]]) -> dict[str, float]:
    """Aggregate retrieval metrics across all queries (macro-average)."""
    if not all_metrics:
        return {}

    keys = all_metrics[0].keys()
    aggregated = {}
    for key in keys:
        values = [m[key] for m in all_metrics if key in m]
        aggregated[key] = sum(values) / len(values) if values else 0.0

    return aggregated
