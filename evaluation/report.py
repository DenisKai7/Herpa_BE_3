"""Report generation v3: Rich tables, CSV, JSON, Markdown, Excel, charts."""

import csv
import json
import logging
from pathlib import Path
from typing import Any

from evaluation.metrics.latency import format_latency_ms

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "results"


def _ensure_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Rich Terminal Report ────────────────────────────────────────────────────

def print_terminal_report(eval_results: dict[str, Any]):
    """Print formatted report using Rich tables."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        from rich import box
        _print_rich(eval_results)
    except ImportError:
        _print_plain(eval_results)


def _print_rich(eval_results: dict[str, Any]):
    """Rich-formatted terminal output."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()
    agg = eval_results.get("aggregated_metrics", {})
    total = eval_results.get("total_queries", 0)
    cached = eval_results.get("cached_count", 0)
    mode = eval_results.get("mode", "full")
    profiling = eval_results.get("profiling", {})

    retrieval = agg.get("retrieval", {})
    judge = agg.get("judge", {})
    citation = agg.get("citation", {})
    graph = agg.get("graph", {})
    latency = agg.get("latency", {})
    overall = agg.get("overall_score", {})

    # Header
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]HERPA GraphRAG Evaluation[/]\n"
        f"Dataset: {total} queries | Mode: {mode} | Cached: {cached}",
        border_style="cyan"
    ))

    # Retrieval table
    t = Table(title="Retrieval Metrics", box=box.ROUNDED, show_lines=False)
    t.add_column("Metric", style="bold")
    t.add_column("Value", justify="right")
    for k in ["precision@1", "precision@3", "precision@5"]:
        t.add_row(k, f"{retrieval.get(k, 0):.4f}")
    for k in ["recall@1", "recall@3", "recall@5"]:
        t.add_row(k, f"{retrieval.get(k, 0):.4f}")
    for k in ["hit_rate@1", "hit_rate@3", "hit_rate@5"]:
        t.add_row(k, f"{retrieval.get(k, 0) * 100:.1f}%")
    t.add_row("MRR", f"{retrieval.get('mrr', 0):.4f}")
    t.add_row("nDCG", f"{retrieval.get('ndcg', 0):.4f}")
    console.print(t)

    # Judge metrics table
    t2 = Table(title="LLM Judge Metrics (1 combined call)", box=box.ROUNDED, show_lines=False)
    t2.add_column("Metric", style="bold")
    t2.add_column("Score", justify="right")
    de_labels = {
        "answer_relevancy": "Answer Relevancy",
        "faithfulness": "Faithfulness",
        "contextual_precision": "Context Precision",
        "contextual_recall": "Context Recall",
        "contextual_relevancy": "Context Relevancy",
        "hallucination_score": "Hallucination (1=none)",
    }
    for key, label in de_labels.items():
        val = judge.get(key, 0.0)
        style = "green" if val >= 0.8 else "yellow" if val >= 0.6 else "red"
        t2.add_row(label, f"[{style}]{val:.4f}[/]")
    console.print(t2)

    # Citation & Graph table
    t3 = Table(title="Citation & Graph", box=box.ROUNDED, show_lines=False)
    t3.add_column("Metric", style="bold")
    t3.add_column("Value", justify="right")
    t3.add_row("Citation Accuracy", f"{citation.get('accuracy', 0) * 100:.1f}%")
    t3.add_row("Node Precision", f"{graph.get('node_precision', 0) * 100:.1f}%")
    t3.add_row("Node Recall", f"{graph.get('node_recall', 0) * 100:.1f}%")
    t3.add_row("Relation Precision", f"{graph.get('relationship_precision', 0) * 100:.1f}%")
    t3.add_row("Relation Recall", f"{graph.get('relationship_recall', 0) * 100:.1f}%")
    t3.add_row("Graph Accuracy", f"{graph.get('overall_accuracy', 0) * 100:.1f}%")
    console.print(t3)

    # Latency table
    t4 = Table(title="Latency", box=box.ROUNDED, show_lines=False)
    t4.add_column("Stage", style="bold")
    t4.add_column("Avg", justify="right")
    t4.add_column("Median", justify="right")
    t4.add_column("P95", justify="right")
    t4.add_column("P99", justify="right")
    for stage in ["embedding", "neo4j", "retrieval", "llm", "total"]:
        stats = latency.get(stage, {})
        t4.add_row(
            stage.capitalize(),
            format_latency_ms(stats.get("avg", 0)),
            format_latency_ms(stats.get("median", 0)),
            format_latency_ms(stats.get("p95", 0)),
            format_latency_ms(stats.get("p99", 0)),
        )
    console.print(t4)

    # Overall score
    score = overall.get("score", 0)
    grade = overall.get("grade", "N/A")
    score_style = "bold green" if score >= 80 else "bold yellow" if score >= 60 else "bold red"
    console.print(Panel.fit(
        f"[{score_style}]{score:.2f} / 100[/]    Grade: [bold]{grade}[/]",
        title="OVERALL SCORE",
        border_style="cyan"
    ))

    # Profiling
    if profiling:
        t5 = Table(title="Profiling", box=box.ROUNDED, show_lines=False)
        t5.add_column("Stage", style="bold")
        t5.add_column("Time", justify="right")
        t5.add_column("%", justify="right")
        total_time = eval_results.get("total_profiling_s", sum(profiling.values()))
        for stage, elapsed in sorted(profiling.items(), key=lambda x: -x[1]):
            pct = (elapsed / total_time * 100) if total_time > 0 else 0
            t5.add_row(stage, f"{elapsed:.1f}s", f"{pct:.0f}%")
        t5.add_row("[bold]TOTAL[/]", f"[bold]{total_time:.1f}s[/]", "100%")
        console.print(t5)

    # Performance stats
    queries_per_sec = total / total_time if total_time > 0 else 0
    avg_per_query = total_time / total if total > 0 else 0
    llm_calls = total - cached
    cache_ratio = cached / total * 100 if total > 0 else 0
    console.print(f"\n  Queries/sec: {queries_per_sec:.1f} | Avg/query: {avg_per_query:.1f}s | "
                  f"LLM calls: {llm_calls} | Cache hit: {cache_ratio:.0f}%")
    console.print()


def _print_plain(eval_results: dict[str, Any]):
    """Fallback plain text output."""
    agg = eval_results.get("aggregated_metrics", {})
    total = eval_results.get("total_queries", 0)
    overall = agg.get("overall_score", {})
    retrieval = agg.get("retrieval", {})
    judge = agg.get("judge", {})
    profiling = eval_results.get("profiling", {})

    w = 30
    print()
    print("=" * (w + 18))
    print(f"{'HERPA GraphRAG Evaluation':^{w + 16}}")
    print(f"{'Dataset: ' + str(total) + ' queries':^{w + 16}}")
    print("=" * (w + 18))

    print("\n  Retrieval Metrics")
    for k in ["precision@1", "precision@3", "precision@5", "recall@1", "recall@3", "recall@5", "mrr", "ndcg"]:
        print(f"    {k:<{w}} {retrieval.get(k, 0):.4f}")
    for k in ["hit_rate@1", "hit_rate@3", "hit_rate@5"]:
        print(f"    {k:<{w}} {retrieval.get(k, 0) * 100:.1f}%")

    print("\n  LLM Judge Metrics")
    for k in ["answer_relevancy", "faithfulness", "contextual_precision", "contextual_recall", "contextual_relevancy", "hallucination_score"]:
        print(f"    {k:<{w}} {judge.get(k, 0):.4f}")

    print(f"\n  OVERALL: {overall.get('score', 0):.2f}/100  Grade: {overall.get('grade', 'N/A')}")

    if profiling:
        print("\n  Profiling:")
        for stage, elapsed in sorted(profiling.items(), key=lambda x: -x[1]):
            print(f"    {stage:<{w}} {elapsed:.1f}s")
    print()


def print_per_query_detail(results: list[dict[str, Any]], max_show: int = 10):
    """Print per-query detail."""
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box
        console = Console()

        t = Table(title=f"Per-Query Detail (first {min(max_show, len(results))})", box=box.ROUNDED)
        t.add_column("ID", style="bold")
        t.add_column("Query", max_width=40)
        t.add_column("P@5", justify="right")
        t.add_column("R@5", justify="right")
        t.add_column("Faith", justify="right")
        t.add_column("AnsRel", justify="right")
        t.add_column("Latency", justify="right")
        t.add_column("Status")

        for r in results[:max_show]:
            ret = r.get("retrieval_metrics", {})
            faith = r.get("faithfulness", 0)
            ans_rel = r.get("answer_relevancy", 0)
            lat = r.get("latency", {})
            status = "[green]PASS[/]" if faith >= 0.7 and ans_rel >= 0.7 else "[yellow]WARN[/]"
            cache = " [dim][cached][/]" if r.get("_from_cache") else ""

            t.add_row(
                str(r.get("id", "?")),
                r.get("query", "")[:40] + cache,
                f"{ret.get('precision@5', 0):.2f}",
                f"{ret.get('recall@5', 0):.2f}",
                f"{faith:.2f}",
                f"{ans_rel:.2f}",
                format_latency_ms(lat.get("total_ms", 0)),
                status,
            )
        console.print(t)
        if len(results) > max_show:
            console.print(f"  ... and {len(results) - max_show} more queries\n")

    except ImportError:
        for r in results[:max_show]:
            ret = r.get("retrieval_metrics", {})
            lat = r.get("latency", {})
            print(f"  Q{r.get('id')}: P@5={ret.get('precision@5',0):.2f} "
                  f"Faith={r.get('faithfulness',0):.2f} "
                  f"Lat={format_latency_ms(lat.get('total_ms',0))}")


# ─── Export Functions ────────────────────────────────────────────────────────

def save_json(eval_results: dict[str, Any]) -> str:
    _ensure_dir()
    path = OUTPUT_DIR / "evaluation_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(eval_results, f, ensure_ascii=False, indent=2, default=str)
    return str(path)


def save_summary_json(eval_results: dict[str, Any]) -> str:
    _ensure_dir()
    path = OUTPUT_DIR / "summary.json"
    summary = {
        "total_queries": eval_results.get("total_queries", 0),
        "cached_count": eval_results.get("cached_count", 0),
        "mode": eval_results.get("mode", "full"),
        "aggregated_metrics": eval_results.get("aggregated_metrics", {}),
        "profiling": eval_results.get("profiling", {}),
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
    return str(path)


def save_csv(eval_results: dict[str, Any]) -> str:
    _ensure_dir()
    path = OUTPUT_DIR / "evaluation_report.csv"
    per_query = eval_results.get("per_query_results", [])
    if not per_query:
        return str(path)

    rows = []
    for r in per_query:
        row = {
            "id": r.get("id"), "query": r.get("query"), "category": r.get("category"),
            "answer": r.get("answer", "")[:500], "ground_truth": r.get("ground_truth", "")[:500],
        }
        ret = r.get("retrieval_metrics", {})
        for k, v in ret.items():
            row[f"retrieval_{k}"] = v
        for k in ["answer_relevancy", "faithfulness", "contextual_precision", "contextual_recall", "contextual_relevancy", "hallucination_score"]:
            row[k] = r.get(k, 0)
        row["citation_accuracy"] = r.get("citation_metrics", {}).get("accuracy", 0)
        graph = r.get("graph_accuracy", {})
        for k in ["node_precision", "node_recall", "relationship_precision", "relationship_recall", "overall_accuracy"]:
            row[f"graph_{k}"] = graph.get(k, 0)
        lat = r.get("latency", {})
        for k in ["retrieval_ms", "llm_ms", "total_ms"]:
            row[f"latency_{k}"] = lat.get(k, 0)
        rows.append(row)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


def save_markdown(eval_results: dict[str, Any]) -> str:
    _ensure_dir()
    path = OUTPUT_DIR / "evaluation_report.md"

    agg = eval_results.get("aggregated_metrics", {})
    total = eval_results.get("total_queries", 0)
    retrieval = agg.get("retrieval", {})
    judge = agg.get("judge", {})
    citation = agg.get("citation", {})
    graph = agg.get("graph", {})
    latency = agg.get("latency", {})
    overall = agg.get("overall_score", {})
    profiling = eval_results.get("profiling", {})

    md = []
    md.append("# Evaluasi Sistem GraphRAG & Agentic AI HERPA\n")
    md.append(f"**Jumlah Query:** {total}\n")
    md.append(f"**Mode:** {eval_results.get('mode', 'full')}\n")
    md.append(f"**Overall Score:** {overall.get('score', 0):.2f} / 100\n")
    md.append(f"**Grade:** {overall.get('grade', 'N/A')}\n")

    md.append("\n## Retrieval Evaluation\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    for k in ["precision@1", "precision@3", "precision@5", "recall@1", "recall@3", "recall@5"]:
        md.append(f"| {k} | {retrieval.get(k, 0):.4f} |")
    for k in ["hit_rate@1", "hit_rate@3", "hit_rate@5"]:
        md.append(f"| {k} | {retrieval.get(k, 0) * 100:.1f}% |")
    md.append(f"| MRR | {retrieval.get('mrr', 0):.4f} |")
    md.append(f"| nDCG | {retrieval.get('ndcg', 0):.4f} |")

    md.append("\n## LLM Judge Metrics\n")
    md.append("| Metric | Score |")
    md.append("|--------|-------|")
    for k, label in [("answer_relevancy","Answer Relevancy"),("faithfulness","Faithfulness"),("contextual_precision","Contextual Precision"),("contextual_recall","Contextual Recall"),("contextual_relevancy","Contextual Relevancy"),("hallucination_score","Hallucination (1=none)")]:
        md.append(f"| {label} | {judge.get(k, 0):.4f} |")

    md.append("\n## Citation & Graph\n")
    md.append("| Metric | Value |")
    md.append("|--------|-------|")
    md.append(f"| Citation Accuracy | {citation.get('accuracy', 0) * 100:.1f}% |")
    md.append(f"| Node Precision | {graph.get('node_precision', 0) * 100:.1f}% |")
    md.append(f"| Node Recall | {graph.get('node_recall', 0) * 100:.1f}% |")
    md.append(f"| Relationship Precision | {graph.get('relationship_precision', 0) * 100:.1f}% |")
    md.append(f"| Relationship Recall | {graph.get('relationship_recall', 0) * 100:.1f}% |")
    md.append(f"| Graph Accuracy | {graph.get('overall_accuracy', 0) * 100:.1f}% |")

    md.append("\n## Latency\n")
    md.append("| Stage | Avg | Median | P95 | P99 |")
    md.append("|-------|-----|--------|-----|-----|")
    for stage in ["embedding", "neo4j", "retrieval", "llm", "total"]:
        stats = latency.get(stage, {})
        md.append(f"| {stage.capitalize()} | {format_latency_ms(stats.get('avg', 0))} | {format_latency_ms(stats.get('median', 0))} | {format_latency_ms(stats.get('p95', 0))} | {format_latency_ms(stats.get('p99', 0))} |")

    if profiling:
        md.append("\n## Profiling\n")
        md.append("| Stage | Time | % |")
        md.append("|-------|------|---|")
        total_time = eval_results.get("total_profiling_s", sum(profiling.values()))
        for stage, elapsed in sorted(profiling.items(), key=lambda x: -x[1]):
            pct = (elapsed / total_time * 100) if total_time > 0 else 0
            md.append(f"| {stage} | {elapsed:.1f}s | {pct:.0f}% |")

    md.append("\n## Kesimpulan\n")
    md.append(f"Berdasarkan evaluasi terhadap {total} query, sistem GraphRAG & Agentic AI HERPA mencapai overall score **{overall.get('score', 0):.2f}/100** dengan grade **{overall.get('grade', 'N/A')}**.\n")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return str(path)


def save_excel(eval_results: dict[str, Any]) -> str:
    _ensure_dir()
    path = OUTPUT_DIR / "evaluation_report.xlsx"
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
    except ImportError:
        return save_csv(eval_results) + " (openpyxl not installed)"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Summary"
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    agg = eval_results.get("aggregated_metrics", {})
    overall = agg.get("overall_score", {})
    ws["A1"] = "HERPA GraphRAG Evaluation"; ws["A1"].font = Font(bold=True, size=14)
    ws["A3"] = "Overall Score"; ws["B3"] = overall.get("score", 0)
    ws["A4"] = "Grade"; ws["B4"] = overall.get("grade", "N/A")
    ws["A5"] = "Total Queries"; ws["B5"] = eval_results.get("total_queries", 0)

    row = 7
    for section, data in [("Retrieval", agg.get("retrieval", {})), ("Judge", agg.get("judge", {})), ("Citation", agg.get("citation", {})), ("Graph", agg.get("graph", {}))]:
        ws[f"A{row}"] = section; ws[f"A{row}"].font = Font(bold=True); row += 1
        for k, v in data.items():
            ws[f"A{row}"] = k; ws[f"B{row}"] = v; row += 1
        row += 1

    # Per-query sheet
    ws2 = wb.create_sheet("Per-Query")
    per_query = eval_results.get("per_query_results", [])
    if per_query:
        headers = ["ID", "Query", "Category", "Precision@5", "Recall@5", "nDCG", "MRR", "Answer Relevancy", "Faithfulness", "Context Precision", "Hallucination", "Citation", "Graph Accuracy", "Latency (ms)"]
        for col, h in enumerate(headers, 1):
            cell = ws2.cell(row=1, column=col, value=h)
            cell.font = header_font; cell.fill = header_fill
        for ri, r in enumerate(per_query, 2):
            ws2.cell(row=ri, column=1, value=r.get("id"))
            ws2.cell(row=ri, column=2, value=r.get("query", "")[:200])
            ws2.cell(row=ri, column=3, value=r.get("category"))
            ret = r.get("retrieval_metrics", {})
            ws2.cell(row=ri, column=4, value=ret.get("precision@5", 0))
            ws2.cell(row=ri, column=5, value=ret.get("recall@5", 0))
            ws2.cell(row=ri, column=6, value=ret.get("ndcg", 0))
            ws2.cell(row=ri, column=7, value=ret.get("mrr", 0))
            ws2.cell(row=ri, column=8, value=r.get("answer_relevancy", 0))
            ws2.cell(row=ri, column=9, value=r.get("faithfulness", 0))
            ws2.cell(row=ri, column=10, value=r.get("contextual_precision", 0))
            ws2.cell(row=ri, column=11, value=r.get("hallucination_score", 0))
            ws2.cell(row=ri, column=12, value=r.get("citation_metrics", {}).get("accuracy", 0))
            ws2.cell(row=ri, column=13, value=r.get("graph_accuracy", {}).get("overall_accuracy", 0))
            ws2.cell(row=ri, column=14, value=r.get("latency", {}).get("total_ms", 0))

    wb.save(path)
    return str(path)


def save_charts(eval_results: dict[str, Any]) -> list[str]:
    """Generate PNG charts if matplotlib available."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []

    _ensure_dir()
    charts_dir = OUTPUT_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    agg = eval_results.get("aggregated_metrics", {})
    retrieval = agg.get("retrieval", {})
    judge = agg.get("judge", {})
    latency = agg.get("latency", {})

    # Precision@k and Recall@k
    fig, ax = plt.subplots(figsize=(8, 5))
    ks = [1, 3, 5]
    prec = [retrieval.get(f"precision@{k}", 0) for k in ks]
    rec = [retrieval.get(f"recall@{k}", 0) for k in ks]
    x = range(len(ks))
    ax.bar([i - 0.15 for i in x], prec, 0.3, label="Precision@k", color="#4472C4")
    ax.bar([i + 0.15 for i in x], rec, 0.3, label="Recall@k", color="#ED7D31")
    ax.set_xlabel("k"); ax.set_ylabel("Score"); ax.set_title("Precision@k vs Recall@k")
    ax.set_xticks(x); ax.set_xticklabels(ks); ax.legend(); ax.set_ylim(0, 1.1)
    p = charts_dir / "precision_recall.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); saved.append(str(p))

    # Judge metrics
    fig, ax = plt.subplots(figsize=(8, 5))
    keys = ["answer_relevancy", "faithfulness", "contextual_precision", "contextual_recall", "contextual_relevancy", "hallucination_score"]
    labels = ["Answer\nRelevancy", "Faithful-\nness", "Context\nPrecision", "Context\nRecall", "Context\nRelevancy", "Hallucination\n(1=none)"]
    vals = [judge.get(k, 0) for k in keys]
    colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
    ax.bar(labels, vals, color=colors)
    ax.set_ylabel("Score"); ax.set_title("LLM Judge Metrics"); ax.set_ylim(0, 1.1)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    p = charts_dir / "judge_metrics.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); saved.append(str(p))

    # Latency
    fig, ax = plt.subplots(figsize=(8, 5))
    stages = ["embedding", "neo4j", "retrieval", "llm", "total"]
    avgs = [latency.get(s, {}).get("avg", 0) for s in stages]
    p95s = [latency.get(s, {}).get("p95", 0) for s in stages]
    x = range(len(stages))
    ax.bar([i - 0.15 for i in x], avgs, 0.3, label="Avg", color="#4472C4")
    ax.bar([i + 0.15 for i in x], p95s, 0.3, label="P95", color="#ED7D31")
    ax.set_xlabel("Stage"); ax.set_ylabel("ms"); ax.set_title("Latency by Stage")
    ax.set_xticks(x); ax.set_xticklabels([s.capitalize() for s in stages]); ax.legend()
    p = charts_dir / "latency.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); saved.append(str(p))

    # Overall pie
    fig, ax = plt.subplots(figsize=(6, 6))
    components = agg.get("overall_score", {}).get("component_scores", {})
    if components:
        labels = [k.replace("_", "\n") for k in components.keys()]
        vals = list(components.values())
        colors = ["#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47", "#264653", "#2A9D8F", "#E76F51"]
        ax.pie(vals, labels=labels, autopct="%1.0f%%", colors=colors[:len(vals)])
        ax.set_title(f"Overall Score: {agg.get('overall_score', {}).get('score', 0):.1f}/100")
    p = charts_dir / "overall.png"
    fig.savefig(p, dpi=150, bbox_inches="tight"); plt.close(fig); saved.append(str(p))

    return saved
