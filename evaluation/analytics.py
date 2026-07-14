"""Analytics aggregation for evaluation results.

Computes Judge Analytics, Neo4j Analytics, Retrieval Analytics,
Citation Analytics, LLM Analytics, and Failure Analysis from
per-query results.
"""

import statistics
from typing import Any


def compute_judge_analytics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute judge performance analytics."""
    judge_times = []
    timeout_count = 0
    retry_count = 0
    success_count = 0
    failure_count = 0
    prompt_tokens_total = 0
    completion_tokens_total = 0

    for r in per_query:
        jlat = r.get("judge_latency_ms", 0)
        if jlat > 0:
            judge_times.append(jlat)

        jsuccess = r.get("judge_success", False)
        jskipped = r.get("judge_skipped", False)
        jerror = r.get("judge_error")

        if jsuccess:
            success_count += 1
        elif jskipped:
            pass  # skipped is not a failure
        else:
            failure_count += 1
            if jerror and "timeout" in str(jerror).lower():
                timeout_count += 1

        # Token usage from judge result
        jtokens = r.get("judge_tokens", {})
        prompt_tokens_total += jtokens.get("prompt_tokens", 0)
        completion_tokens_total += jtokens.get("completion_tokens", 0)
        retry_count += jtokens.get("retries", 0)

    return {
        "judge_model": per_query[0].get("judge_model", "unknown") if per_query else "unknown",
        "judge_prompt_version": per_query[0].get("judge_prompt_version", "v1") if per_query else "v1",
        "total_judge_calls": success_count + failure_count,
        "prompt_tokens": prompt_tokens_total,
        "completion_tokens": completion_tokens_total,
        "total_tokens": prompt_tokens_total + completion_tokens_total,
        "average_judge_time_ms": round(statistics.mean(judge_times), 2) if judge_times else 0,
        "slowest_judge_ms": round(max(judge_times), 2) if judge_times else 0,
        "fastest_judge_ms": round(min(judge_times), 2) if judge_times else 0,
        "timeout_count": timeout_count,
        "retry_count": retry_count,
        "success_count": success_count,
        "failure_count": failure_count,
    }


def compute_neo4j_analytics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute Neo4j query analytics."""
    neo4j_times = []
    total_nodes = 0
    total_relations = 0

    for r in per_query:
        lat = r.get("latency", {})
        ntime = lat.get("neo4j_ms", 0)
        if ntime > 0:
            neo4j_times.append(ntime)

        total_nodes += len(r.get("retrieved_nodes", []))
        total_relations += len(r.get("retrieved_relations", []))

    n = len(per_query) or 1

    return {
        "neo4j_calls": sum(1 for r in per_query if r.get("latency", {}).get("neo4j_ms", 0) > 0),
        "average_query_time_ms": round(statistics.mean(neo4j_times), 2) if neo4j_times else 0,
        "median_query_time_ms": round(statistics.median(neo4j_times), 2) if neo4j_times else 0,
        "fastest_query_ms": round(min(neo4j_times), 2) if neo4j_times else 0,
        "slowest_query_ms": round(max(neo4j_times), 2) if neo4j_times else 0,
        "total_nodes_retrieved": total_nodes,
        "total_relations_retrieved": total_relations,
        "average_nodes_per_query": round(total_nodes / n, 2),
        "average_relations_per_query": round(total_relations / n, 2),
    }


def compute_retrieval_analytics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute retrieval quality analytics."""
    all_nodes = []
    all_relations = []
    depths = []
    breadths = []

    for r in per_query:
        nodes = r.get("retrieved_nodes", [])
        rels = r.get("retrieved_relations", [])
        all_nodes.append(len(nodes))
        all_relations.append(len(rels))

        audit = r.get("retrieval_audit", {})
        depths.append(audit.get("graph_depth", 0))
        breadths.append(audit.get("graph_breadth", 0))

    n = len(per_query) or 1

    return {
        "average_retrieved_nodes": round(sum(all_nodes) / n, 2),
        "average_retrieved_relations": round(sum(all_relations) / n, 2),
        "average_graph_depth": round(sum(depths) / n, 2) if depths else 0,
        "average_graph_breadth": round(sum(breadths) / n, 2) if breadths else 0,
    }


def compute_citation_analytics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute citation quality analytics."""
    total_correct = 0
    total_incorrect = 0
    total_missing = 0
    total_citations = 0
    coverage_count = 0
    completeness_count = 0

    for r in per_query:
        cit = r.get("citation_metrics", {})
        total_correct += cit.get("correct", 0)
        total_incorrect += cit.get("incorrect", 0)
        total_missing += cit.get("missing", 0)
        details = cit.get("details", [])
        total_citations += len(details)

        # Coverage: answer has at least one citation
        if details:
            coverage_count += 1
        # Completeness: all expected citations found
        if cit.get("missing", 0) == 0 and cit.get("incorrect", 0) == 0:
            completeness_count += 1

    n = len(per_query) or 1
    total = total_correct + total_incorrect

    return {
        "citation_accuracy": round(total_correct / total, 4) if total > 0 else 1.0,
        "citation_coverage": round(coverage_count / n, 4),
        "citation_completeness": round(completeness_count / n, 4),
        "missing_citations": total_missing,
        "broken_citations": total_incorrect,
        "average_citation_count": round(total_citations / n, 2),
    }


def compute_llm_analytics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute LLM generation analytics."""
    llm_times = []
    prompt_tokens_list = []
    completion_tokens_list = []
    generation_speeds = []

    for r in per_query:
        lat = r.get("latency", {})
        llm_ms = lat.get("llm_ms", 0)
        if llm_ms > 0:
            llm_times.append(llm_ms)

        # Token usage from agent result
        tokens = r.get("agent_tokens", {})
        pt = tokens.get("prompt_tokens", 0)
        ct = tokens.get("completion_tokens", 0)
        if pt > 0:
            prompt_tokens_list.append(pt)
        if ct > 0:
            completion_tokens_list.append(ct)

        # Generation speed: tokens/sec
        if ct > 0 and llm_ms > 0:
            speed = ct / (llm_ms / 1000)
            generation_speeds.append(speed)

    n = len(per_query) or 1

    return {
        "llm_calls": sum(1 for r in per_query if r.get("latency", {}).get("llm_ms", 0) > 0),
        "average_prompt_tokens": round(statistics.mean(prompt_tokens_list), 0) if prompt_tokens_list else 0,
        "average_completion_tokens": round(statistics.mean(completion_tokens_list), 0) if completion_tokens_list else 0,
        "average_total_tokens": round(
            statistics.mean([p + c for p, c in zip(prompt_tokens_list, completion_tokens_list)]), 0
        ) if prompt_tokens_list and completion_tokens_list else 0,
        "generation_speed_tps": round(statistics.mean(generation_speeds), 1) if generation_speeds else 0,
        "average_response_time_ms": round(statistics.mean(llm_times), 2) if llm_times else 0,
    }


def compute_failure_analysis(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Categorize failures by root cause."""
    categories: dict[str, int] = {}
    details: list[dict[str, Any]] = []

    for r in per_query:
        if r.get("status") == "PASS":
            continue

        errors = r.get("errors", [])
        category = _categorize_failure(errors, r)

        categories[category] = categories.get(category, 0) + 1
        details.append({
            "id": r.get("id"),
            "query": r.get("query", "")[:80],
            "status": r.get("status"),
            "category": category,
            "errors": errors[:3],  # Top 3 errors
        })

    return {
        "total_failures": len(details),
        "categories": categories,
        "details": details,
    }


def _categorize_failure(errors: list[str], result: dict[str, Any]) -> str:
    """Categorize a failure by root cause."""
    error_text = " ".join(errors).lower()

    if "entity" in error_text and "not found" in error_text:
        return "entity_not_found"
    if "neo4j" in error_text and "timeout" in error_text:
        return "neo4j_timeout"
    if "judge" in error_text and "timeout" in error_text:
        return "judge_timeout"
    if "llm" in error_text and "timeout" in error_text:
        return "llm_timeout"
    if "empty" in error_text and ("context" in error_text or "answer" in error_text):
        return "context_empty"
    if "citation" in error_text and "missing" in error_text:
        return "citation_missing"
    # Removed: hallucination category (not applicable to GraphRAG)
    if "json" in error_text and ("invalid" in error_text or "parse" in error_text):
        return "output_invalid_json"
    if "prompt" in error_text and "too long" in error_text:
        return "prompt_too_long"
    if "graph" in error_text and "disconnect" in error_text:
        return "graph_disconnected"
    if "empty answer" in error_text:
        return "empty_answer"
    if "pipeline" in error_text:
        return "pipeline_error"
    return "unknown"


def compute_all_analytics(per_query: list[dict[str, Any]], eval_results: dict[str, Any]) -> dict[str, Any]:
    """Compute all analytics sections."""
    return {
        "judge": compute_judge_analytics(per_query),
        "neo4j": compute_neo4j_analytics(per_query),
        "retrieval": compute_retrieval_analytics(per_query),
        "citation": compute_citation_analytics(per_query),
        "llm": compute_llm_analytics(per_query),
        "failure_analysis": compute_failure_analysis(per_query),
    }
