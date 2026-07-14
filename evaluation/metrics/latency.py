"""Latency measurement for each pipeline stage.

Enhanced with judge, Neo4j, graph expansion, and ranking stages.
All timing uses time.perf_counter() (monotonic) for consistency.
"""

import statistics
from typing import Any


def compute_latency_stats(measurements: list[float]) -> dict[str, float]:
    """Compute latency statistics: avg, median, min, max, p95, p99."""
    if not measurements:
        return {"avg": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "p95": 0.0, "p99": 0.0}

    sorted_vals = sorted(measurements)
    n = len(sorted_vals)

    avg = statistics.mean(sorted_vals)
    median = statistics.median(sorted_vals)
    min_val = sorted_vals[0]
    max_val = sorted_vals[-1]

    p95_idx = int(n * 0.95)
    p95 = sorted_vals[min(p95_idx, n - 1)]

    p99_idx = int(n * 0.99)
    p99 = sorted_vals[min(p99_idx, n - 1)]

    return {
        "avg": round(avg, 2),
        "median": round(median, 2),
        "min": round(min_val, 2),
        "max": round(max_val, 2),
        "p95": round(p95, 2),
        "p99": round(p99, 2),
    }


def format_latency_ms(value: float) -> str:
    """Format latency value for display."""
    if value >= 1000:
        return f"{value / 1000:.2f} s"
    return f"{value:.0f} ms"


def create_latency_record(
    embedding_ms: float = 0.0,
    neo4j_ms: float = 0.0,
    retrieval_ms: float = 0.0,
    llm_ms: float = 0.0,
    judge_ms: float = 0.0,
    graph_expansion_ms: float = 0.0,
    ranking_ms: float = 0.0,
    total_ms: float = 0.0,
) -> dict[str, float]:
    """Create a latency record for a single query."""
    return {
        "embedding_ms": embedding_ms,
        "neo4j_ms": neo4j_ms,
        "retrieval_ms": retrieval_ms,
        "llm_ms": llm_ms,
        "judge_ms": judge_ms,
        "graph_expansion_ms": graph_expansion_ms,
        "ranking_ms": ranking_ms,
        "total_ms": total_ms,
    }


def aggregate_latency(all_records: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    """Aggregate latency statistics across all queries.

    Returns dict with stats for each stage including new judge/neo4j stages.
    """
    stage_keys = {
        "embedding": "embedding_ms",
        "neo4j": "neo4j_ms",
        "retrieval": "retrieval_ms",
        "llm": "llm_ms",
        "judge": "judge_ms",
        "graph_expansion": "graph_expansion_ms",
        "ranking": "ranking_ms",
        "total": "total_ms",
    }

    aggregated = {}
    for stage_name, record_key in stage_keys.items():
        measurements = [r.get(record_key, 0.0) for r in all_records if r.get(record_key, 0.0) > 0]
        aggregated[stage_name] = compute_latency_stats(measurements)

    return aggregated


def compute_generation_speed(per_query: list[dict[str, Any]]) -> float:
    """Compute average generation speed in tokens/sec."""
    speeds = []
    for r in per_query:
        tokens = r.get("agent_tokens", {})
        ct = tokens.get("completion_tokens", 0)
        llm_ms = r.get("latency", {}).get("llm_ms", 0)
        if ct > 0 and llm_ms > 0:
            speeds.append(ct / (llm_ms / 1000))
    return round(statistics.mean(speeds), 1) if speeds else 0.0
