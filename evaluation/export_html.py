"""HTML report exporter for evaluation results.

Generates a self-contained HTML report with:
- Executive Summary
- Metric tables
- Per-query details
- Neo4j analytics
- Graph analytics
- Citation analytics
- Judge analytics
- Failure analysis
- Recommendations
"""

from typing import Any
from pathlib import Path


def _safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    return default


def generate_html_report(eval_results: dict[str, Any], analytics: dict[str, Any], output_path: str) -> str:
    """Generate a complete HTML report."""
    agg = eval_results.get("aggregated_metrics", {})
    total = eval_results.get("total_queries", 0)
    success = eval_results.get("success_count", 0)
    skipped = eval_results.get("skip_count", 0)
    failed = eval_results.get("fail_count", 0)
    mode = eval_results.get("mode", "full")
    overall = agg.get("overall_score", {})
    profiling = eval_results.get("profiling", {})
    per_query = eval_results.get("per_query_results", [])

    retrieval = agg.get("retrieval", {})
    judge = agg.get("judge", {})
    citation = agg.get("citation", {})
    graph = agg.get("graph", {})
    latency = agg.get("latency", {})

    judge_analytics = analytics.get("judge", {})
    neo4j_analytics = analytics.get("neo4j", {})
    retrieval_analytics = analytics.get("retrieval", {})
    citation_analytics = analytics.get("citation", {})
    llm_analytics = analytics.get("llm", {})
    failure_analysis = analytics.get("failure_analysis", {})

    score = overall.get("score", 0)
    grade = overall.get("grade", "N/A")

    html = f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>HERPA GraphRAG Evaluation Report</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
h1 {{ color: #1a5276; border-bottom: 3px solid #2980b9; padding-bottom: 10px; margin-bottom: 20px; }}
h2 {{ color: #2c3e50; margin: 30px 0 15px; border-left: 4px solid #2980b9; padding-left: 10px; }}
h3 {{ color: #34495e; margin: 20px 0 10px; }}
.card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
.score-box {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; margin: 20px 0; }}
.score-box .score {{ font-size: 48px; font-weight: bold; }}
.score-box .grade {{ font-size: 24px; margin-top: 5px; }}
table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #eee; }}
th {{ background: #f8f9fa; font-weight: 600; color: #2c3e50; }}
tr:hover {{ background: #f5f5f5; }}
.metric-value {{ font-weight: bold; color: #2980b9; }}
.good {{ color: #27ae60; }}
.warning {{ color: #f39c12; }}
.bad {{ color: #e74c3c; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
.status-pass {{ color: #27ae60; font-weight: bold; }}
.status-skip {{ color: #f39c12; font-weight: bold; }}
.status-fail {{ color: #e74c3c; font-weight: bold; }}
.recommendation {{ background: #eaf2f8; border-left: 4px solid #2980b9; padding: 15px; margin: 10px 0; border-radius: 4px; }}
.warning-box {{ background: #fef9e7; border-left: 4px solid #f39c12; padding: 15px; margin: 10px 0; border-radius: 4px; }}
footer {{ text-align: center; padding: 20px; color: #7f8c8d; font-size: 14px; margin-top: 40px; }}
</style>
</head>
<body>
<div class="container">

<h1>HERPA GraphRAG &amp; Agentic AI — Evaluation Report</h1>

<div class="card">
<p><strong>Mode:</strong> {mode} | <strong>Queries:</strong> {total} | <strong>Success:</strong> {success} | <strong>Skipped:</strong> {skipped} | <strong>Failed:</strong> {failed}</p>
<p><strong>Total Time:</strong> {eval_results.get('total_profiling_s', 0):.1f}s | <strong>LLM Calls:</strong> {eval_results.get('llm_calls', 0)} | <strong>Neo4j Calls:</strong> {eval_results.get('neo4j_calls', 0)}</p>
</div>

<div class="score-box">
<div class="score">{score:.2f} / 100</div>
<div class="grade">Grade: {grade}</div>
</div>

<h2>1. Retrieval Metrics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
{_metric_rows(retrieval, ["precision@1","precision@3","precision@5","recall@1","recall@3","recall@5","hit_rate@1","hit_rate@3","hit_rate@5","mrr","ndcg"])}
</table>
</div>

<h2>2. Generation (LLM Evaluation)</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Score</th></tr>
<tr><td>Answer Relevancy</td><td class="metric-value">{_safe_float(judge.get('answer_relevancy')):.4f}</td></tr>
</table>
</div>

<h2>3. Citation &amp; Graph</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Citation Accuracy</td><td class="metric-value">{citation.get('accuracy', 0) * 100:.1f}%</td></tr>
<tr><td>Node Precision</td><td class="metric-value">{graph.get('node_precision', 0) * 100:.1f}%</td></tr>
<tr><td>Node Recall</td><td class="metric-value">{graph.get('node_recall', 0) * 100:.1f}%</td></tr>
<tr><td>Relationship Precision</td><td class="metric-value">{graph.get('relationship_precision', 0) * 100:.1f}%</td></tr>
<tr><td>Relationship Recall</td><td class="metric-value">{graph.get('relationship_recall', 0) * 100:.1f}%</td></tr>
<tr><td>Graph Accuracy</td><td class="metric-value">{graph.get('overall_accuracy', 0) * 100:.1f}%</td></tr>
</table>
</div>

<h2>4. Latency</h2>
<div class="card">
<table>
<tr><th>Stage</th><th>Avg</th><th>Median</th><th>P95</th><th>P99</th></tr>
{_latency_rows(latency)}
</table>
</div>

<h2>5. Overall Score Breakdown</h2>
<div class="card">
<table>
<tr><th>Component</th><th>Score</th><th>Weight</th></tr>
{_overall_rows(overall)}
</table>
</div>

<h2>6. Judge Analytics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Judge Model</td><td>{judge_analytics.get('judge_model', 'N/A')}</td></tr>
<tr><td>Prompt Version</td><td>{judge_analytics.get('judge_prompt_version', 'N/A')}</td></tr>
<tr><td>Prompt Tokens (total)</td><td>{judge_analytics.get('prompt_tokens', 0)}</td></tr>
<tr><td>Completion Tokens (total)</td><td>{judge_analytics.get('completion_tokens', 0)}</td></tr>
<tr><td>Total Tokens</td><td>{judge_analytics.get('total_tokens', 0)}</td></tr>
<tr><td>Average Judge Time</td><td>{judge_analytics.get('average_judge_time_ms', 0):.0f} ms</td></tr>
<tr><td>Slowest Judge</td><td>{judge_analytics.get('slowest_judge_ms', 0):.0f} ms</td></tr>
<tr><td>Fastest Judge</td><td>{judge_analytics.get('fastest_judge_ms', 0):.0f} ms</td></tr>
<tr><td>Timeout Count</td><td>{judge_analytics.get('timeout_count', 0)}</td></tr>
<tr><td>Retry Count</td><td>{judge_analytics.get('retry_count', 0)}</td></tr>
<tr><td>Success Count</td><td>{judge_analytics.get('success_count', 0)}</td></tr>
<tr><td>Failure Count</td><td>{judge_analytics.get('failure_count', 0)}</td></tr>
</table>
</div>

<h2>7. Neo4j Analytics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Neo4j Calls</td><td>{neo4j_analytics.get('neo4j_calls', 0)}</td></tr>
<tr><td>Average Query Time</td><td>{neo4j_analytics.get('average_query_time_ms', 0):.0f} ms</td></tr>
<tr><td>Median Query Time</td><td>{neo4j_analytics.get('median_query_time_ms', 0):.0f} ms</td></tr>
<tr><td>Fastest Query</td><td>{neo4j_analytics.get('fastest_query_ms', 0):.0f} ms</td></tr>
<tr><td>Slowest Query</td><td>{neo4j_analytics.get('slowest_query_ms', 0):.0f} ms</td></tr>
<tr><td>Total Nodes Retrieved</td><td>{neo4j_analytics.get('total_nodes_retrieved', 0)}</td></tr>
<tr><td>Total Relations Retrieved</td><td>{neo4j_analytics.get('total_relations_retrieved', 0)}</td></tr>
<tr><td>Average Nodes/Query</td><td>{neo4j_analytics.get('average_nodes_per_query', 0):.1f}</td></tr>
<tr><td>Average Relations/Query</td><td>{neo4j_analytics.get('average_relations_per_query', 0):.1f}</td></tr>
</table>
</div>

<h2>8. Retrieval Analytics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Average Retrieved Nodes</td><td>{retrieval_analytics.get('average_retrieved_nodes', 0):.1f}</td></tr>
<tr><td>Average Retrieved Relations</td><td>{retrieval_analytics.get('average_retrieved_relations', 0):.1f}</td></tr>
<tr><td>Average Graph Depth</td><td>{retrieval_analytics.get('average_graph_depth', 0):.1f}</td></tr>
<tr><td>Average Graph Breadth</td><td>{retrieval_analytics.get('average_graph_breadth', 0):.1f}</td></tr>
</table>
</div>

<h2>9. Citation Analytics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Citation Accuracy</td><td>{citation_analytics.get('citation_accuracy', 0) * 100:.1f}%</td></tr>
<tr><td>Citation Coverage</td><td>{citation_analytics.get('citation_coverage', 0) * 100:.1f}%</td></tr>
<tr><td>Citation Completeness</td><td>{citation_analytics.get('citation_completeness', 0) * 100:.1f}%</td></tr>
<tr><td>Missing Citations</td><td>{citation_analytics.get('missing_citations', 0)}</td></tr>
<tr><td>Broken Citations</td><td>{citation_analytics.get('broken_citations', 0)}</td></tr>
<tr><td>Average Citation Count</td><td>{citation_analytics.get('average_citation_count', 0):.1f}</td></tr>
</table>
</div>

<h2>10. LLM Analytics</h2>
<div class="card">
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>LLM Calls</td><td>{llm_analytics.get('llm_calls', 0)}</td></tr>
<tr><td>Average Prompt Tokens</td><td>{llm_analytics.get('average_prompt_tokens', 0):.0f}</td></tr>
<tr><td>Average Completion Tokens</td><td>{llm_analytics.get('average_completion_tokens', 0):.0f}</td></tr>
<tr><td>Average Total Tokens</td><td>{llm_analytics.get('average_total_tokens', 0):.0f}</td></tr>
<tr><td>Generation Speed</td><td>{llm_analytics.get('generation_speed_tps', 0):.1f} tokens/sec</td></tr>
<tr><td>Average Response Time</td><td>{llm_analytics.get('average_response_time_ms', 0):.0f} ms</td></tr>
</table>
</div>

<h2>11. Per-Query Results</h2>
<div class="card">
<table>
<tr><th>ID</th><th>Query</th><th>Nodes</th><th>Rels</th><th>Ctx</th><th>Ans</th><th>AnsRel</th><th>Latency</th><th>Status</th></tr>
{_per_query_rows(per_query[:20])}
</table>
{f'<p><em>Showing first 20 of {len(per_query)} queries</em></p>' if len(per_query) > 20 else ''}
</div>

<h2>12. Failure Analysis</h2>
<div class="card">
{_failure_analysis_html(failure_analysis)}
</div>

<h2>13. Profiling</h2>
<div class="card">
<table>
<tr><th>Stage</th><th>Time</th><th>%</th></tr>
{_profiling_rows(profiling, eval_results.get('total_profiling_s', 0))}
</table>
</div>

<h2>14. Recommendations</h2>
<div class="card">
{_recommendations_html(retrieval, judge, citation, graph, latency, failure_analysis, judge_analytics)}
</div>

<footer>
HERPA GraphRAG &amp; Agentic AI Evaluation System &mdash; Generated Report
</footer>

</div>
</body>
</html>"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path


def _metric_rows(data: dict, keys: list[str]) -> str:
    rows = []
    for k in keys:
        val = data.get(k, 0)
        if "hit_rate" in k:
            rows.append(f'<tr><td>{k}</td><td class="metric-value">{val * 100:.1f}%</td></tr>')
        else:
            rows.append(f'<tr><td>{k}</td><td class="metric-value">{val:.4f}</td></tr>')
    return "\n".join(rows)


def _judge_rows(judge: dict) -> str:
    labels = {
        "answer_relevancy": "Answer Relevancy",
    }
    rows = []
    for key, label in labels.items():
        val = _safe_float(judge.get(key))
        cls = "good" if val >= 0.8 else "warning" if val >= 0.6 else "bad"
        rows.append(f'<tr><td>{label}</td><td class="metric-value {cls}">{val:.4f}</td></tr>')
    return "\n".join(rows)


def _latency_rows(latency: dict) -> str:
    rows = []
    for stage in ["embedding", "neo4j", "retrieval", "llm", "judge", "total"]:
        stats = latency.get(stage, {})
        if not stats or stats.get("avg", 0) == 0:
            continue
        rows.append(
            f'<tr><td>{stage.capitalize()}</td>'
            f'<td>{stats.get("avg", 0):.0f} ms</td>'
            f'<td>{stats.get("median", 0):.0f} ms</td>'
            f'<td>{stats.get("p95", 0):.0f} ms</td>'
            f'<td>{stats.get("p99", 0):.0f} ms</td></tr>'
        )
    return "\n".join(rows)


def _overall_rows(overall: dict) -> str:
    scores = overall.get("component_scores", {})
    weights = overall.get("weights", {})
    sub_scores = overall.get("sub_scores", {})
    rows = []
    label_map = {
        "retrieval": "Retrieval",
        "answer_relevancy": "Generation",
        "graph": "Graph",
        "citation": "Citation",
        "latency": "Performance",
    }
    for key, score in scores.items():
        w = weights.get(key, 0)
        label = label_map.get(key, key.replace("_", " ").title())
        cls = "good" if score >= 80 else "warning" if score >= 60 else "bad"
        rows.append(f'<tr><td>{label}</td><td class="metric-value {cls}">{score:.1f}</td><td>{w:.0%}</td></tr>')

    # Add sub-scores detail
    ret_sub = sub_scores.get("retrieval", {})
    if ret_sub:
        for k, v in ret_sub.items():
            rows.append(f'<tr><td style="padding-left:20px">↳ {k}</td><td>{v:.4f}</td><td></td></tr>')

    graph_sub = sub_scores.get("graph", {})
    if graph_sub:
        for k, v in graph_sub.items():
            rows.append(f'<tr><td style="padding-left:20px">↳ {k.replace("_", " ").title()}</td><td>{v:.4f}</td><td></td></tr>')

    return "\n".join(rows)


def _per_query_rows(results: list[dict]) -> str:
    rows = []
    for r in results:
        status = r.get("status", "UNKNOWN")
        cls = f"status-{status.lower()}"
        ans_rel = _safe_float(r.get("answer_relevancy"))
        lat = r.get("latency", {})
        rows.append(
            f'<tr>'
            f'<td>{r.get("id", "?")}</td>'
            f'<td>{r.get("query", "")[:50]}</td>'
            f'<td>{len(r.get("retrieved_nodes", []))}</td>'
            f'<td>{len(r.get("retrieved_relations", []))}</td>'
            f'<td>{r.get("context_size", 0)}</td>'
            f'<td>{r.get("answer_length", 0)}</td>'
            f'<td>{ans_rel:.2f}</td>'
            f'<td>{lat.get("total_ms", 0):.0f} ms</td>'
            f'<td class="{cls}">{status}</td>'
            f'</tr>'
        )
    return "\n".join(rows)


def _failure_analysis_html(failure: dict) -> str:
    if not failure or failure.get("total_failures", 0) == 0:
        return "<p>No failures detected.</p>"

    html = f'<p><strong>Total Failures:</strong> {failure.get("total_failures", 0)}</p>'
    html += '<h3>Categories</h3><table><tr><th>Category</th><th>Count</th></tr>'
    for cat, count in failure.get("categories", {}).items():
        html += f'<tr><td>{cat.replace("_", " ").title()}</td><td>{count}</td></tr>'
    html += '</table>'

    details = failure.get("details", [])
    if details:
        html += '<h3>Details</h3><table><tr><th>ID</th><th>Query</th><th>Category</th><th>Errors</th></tr>'
        for d in details[:10]:
            errors = "; ".join(d.get("errors", [])[:2])
            html += f'<tr><td>{d.get("id", "?")}</td><td>{d.get("query", "")[:40]}</td><td>{d.get("category", "").replace("_", " ").title()}</td><td>{errors[:80]}</td></tr>'
        html += '</table>'

    return html


def _profiling_rows(profiling: dict, total_time: float) -> str:
    rows = []
    for stage, elapsed in sorted(profiling.items(), key=lambda x: -x[1]):
        pct = (elapsed / total_time * 100) if total_time > 0 else 0
        rows.append(f'<tr><td>{stage}</td><td>{elapsed:.1f}s</td><td>{pct:.0f}%</td></tr>')
    rows.append(f'<tr><td><strong>TOTAL</strong></td><td><strong>{total_time:.1f}s</strong></td><td>100%</td></tr>')
    return "\n".join(rows)


def _recommendations_html(retrieval, judge, citation, graph, latency, failure, judge_analytics) -> str:
    recs = []

    # Retrieval recommendations
    p5 = retrieval.get("precision@5", 0)
    if p5 < 0.8:
        recs.append(f'<div class="recommendation"><strong>Retrieval:</strong> Precision@5 is {p5:.2f} (target: &gt;0.80). Consider improving entity resolution or adding more specific Cypher query templates.</div>')

    r5 = retrieval.get("recall@5", 0)
    if r5 < 0.75:
        recs.append(f'<div class="recommendation"><strong>Retrieval:</strong> Recall@5 is {r5:.2f} (target: &gt;0.75). Graph expansion may be missing relevant nodes. Consider increasing retrieval depth.</div>')

    # Judge recommendations
    ans_rel = _safe_float(judge.get("answer_relevancy"))
    if ans_rel < 0.8:
        recs.append(f'<div class="recommendation"><strong>Answer Relevancy:</strong> Score is {ans_rel:.2f} (target: &gt;0.80). LLM may be generating answers not relevant to the question.</div>')

    timeouts = judge_analytics.get("timeout_count", 0)
    if timeouts > 0:
        recs.append(f'<div class="warning-box"><strong>Judge Timeouts:</strong> {timeouts} queries timed out. Consider increasing timeout or reducing context size.</div>')

    # Citation recommendations
    cit_acc = citation.get("accuracy", 0)
    if cit_acc < 0.95:
        recs.append(f'<div class="recommendation"><strong>Citations:</strong> Accuracy is {cit_acc * 100:.1f}% (target: &gt;95%). Some citations may not match retrieved graph nodes.</div>')

    # Graph recommendations
    graph_acc = graph.get("overall_accuracy", 0)
    if graph_acc < 0.85:
        recs.append(f'<div class="recommendation"><strong>Graph Accuracy:</strong> Score is {graph_acc * 100:.1f}% (target: &gt;85%). Node/relationship matching may need improvement.</div>')

    # Failure recommendations
    categories = failure.get("categories", {})
    if categories.get("entity_not_found", 0) > 0:
        recs.append(f'<div class="warning-box"><strong>Entity Not Found:</strong> {categories["entity_not_found"]} queries failed due to unrecognized entities. Expand the entity resolver dictionary.</div>')
    if categories.get("context_empty", 0) > 0:
        recs.append(f'<div class="warning-box"><strong>Empty Context:</strong> {categories["context_empty"]} queries had empty retrieval results. Check Neo4j data and query templates.</div>')

    if not recs:
        recs.append('<div class="recommendation"><strong>All metrics meet targets.</strong> No critical recommendations at this time.</div>')

    return "\n".join(recs)
