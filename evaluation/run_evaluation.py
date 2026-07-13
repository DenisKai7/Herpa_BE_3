"""HERPA GraphRAG Evaluation Runner v3.

Run with:
    python evaluation/run_evaluation.py                  # Full mode
    python evaluation/run_evaluation.py --quick          # Quick: 20 queries
    python evaluation/run_evaluation.py --clear-cache    # Force re-evaluation
    python evaluation/run_evaluation.py --concurrent 10  # Higher parallelism

Requires: .env with Neo4j, llama.cpp running at 127.0.0.1:8080
"""

import argparse
import asyncio
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluator import Evaluator, EvalMode
from evaluation.report import (
    print_per_query_detail,
    print_terminal_report,
    save_csv,
    save_excel,
    save_json,
    save_markdown,
    save_summary_json,
    save_charts,
)


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in ["neo4j", "httpx", "httpcore", "openai", "litellm"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ─── Rich Progress ───────────────────────────────────────────────────────────

class RichProgress:
    """Rich-based progress display with stages."""

    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.stage = ""
        self.start_time = time.perf_counter()
        self._lock = asyncio.Lock()
        self._console = None
        self._progress = None
        self._task = None

        try:
            from rich.console import Console
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
            self._console = Console()
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=30),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TextColumn("({task.completed}/{task.total})"),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=self._console,
            )
            self._use_rich = True
        except ImportError:
            self._use_rich = False

    def start(self):
        if self._use_rich and self._progress:
            self._progress.start()
            self._task = self._progress.add_task("Evaluating...", total=self.total)

    async def update(self, current: int, stage: str = ""):
        async with self._lock:
            self.current = current
            if stage:
                self.stage = stage

            if self._use_rich and self._progress and self._task is not None:
                stage_labels = {
                    "cached": "[dim]Cached[/]",
                    "retrieving": "[cyan]Retrieving[/]",
                    "generating": "[yellow]Generating[/]",
                    "metrics": "[green]Metrics[/]",
                    "judging": "[magenta]Judging[/]",
                    "done": "[green]Done[/]",
                }
                label = stage_labels.get(stage, stage)
                self._progress.update(self._task, completed=current, description=f"{label}")
            else:
                # Plain fallback
                bar_width = 30
                pct = current / self.total if self.total > 0 else 0
                filled = int(bar_width * pct)
                bar = "█" * filled + "░" * (bar_width - filled)
                elapsed = time.perf_counter() - self.start_time
                rate = current / elapsed if elapsed > 0 else 0
                remaining = (self.total - current) / rate if rate > 0 else 0
                eta = f"{remaining:.0f}s" if remaining > 0 else "done"
                sys.stdout.write(f"\r  {stage:<12} [{bar}] {current}/{self.total}  ETA: {eta}   ")
                sys.stdout.flush()

    def stop(self):
        if self._use_rich and self._progress:
            self._progress.stop()
        else:
            bar_width = 30
            bar = "█" * bar_width
            elapsed = time.perf_counter() - self.start_time
            sys.stdout.write(f"\r  {'Complete':<12} [{bar}] {self.total}/{self.total}  {elapsed:.1f}s          \n")
            sys.stdout.flush()


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(description="HERPA GraphRAG Evaluation Framework")
    parser.add_argument("--mode", choices=["quick", "standard", "full"], default="quick",
                        help="Evaluation mode: quick (10q, <3min), standard (30q, <10min), full (100q)")
    parser.add_argument("--concurrent", type=int, default=5, help="Max concurrent queries (default: 5)")
    parser.add_argument("--no-cache", action="store_true", help="Disable result caching")
    parser.add_argument("--clear-cache", action="store_true", help="Clear cache before running")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--no-excel", action="store_true", help="Skip Excel generation")
    parser.add_argument("--no-charts", action="store_true", help="Skip chart generation")
    parser.add_argument("--show-detail", type=int, default=10, help="Show per-query detail for N queries")
    parser.add_argument("--workers", type=int, default=0, help="Thread pool workers (default: auto)")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("evaluation")

    mode = EvalMode(args.mode)

    mode_labels = {"quick": "Quick (10q, <3min)", "standard": "Standard (30q, <10min)", "full": "Full (100q)"}

    try:
        from rich.console import Console
        console = Console()
        console.print()
        console.print("[bold cyan]══════════════════════════════════════════════════════════════[/]")
        console.print("[bold cyan]    HERPA GraphRAG & Agentic AI Evaluation[/]")
        console.print(f"[bold cyan]    Mode: {mode_labels.get(mode.value, mode.value)}[/]")
        console.print("[bold cyan]══════════════════════════════════════════════════════════════[/]")
        console.print()
    except ImportError:
        print()
        print("=" * 60)
        print(f"    HERPA GraphRAG Evaluation — {mode_labels.get(mode.value, mode.value)}")
        print("=" * 60)
        print()

    evaluator = Evaluator(
        max_concurrent=args.concurrent,
        mode=mode,
        use_cache=not args.no_cache,
        clear_cache=args.clear_cache,
        max_workers=args.workers,
    )

    # Setup
    try:
        await evaluator.setup()
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"\n  ERROR: {e}")
        print("  Pastikan .env benar dan Neo4j + llama.cpp berjalan.\n")
        sys.exit(1)

    total = len(evaluator.test_queries)
    try:
        from rich.console import Console
        console = Console()
        console.print(f"  Dataset: [bold]{total}[/] queries | Mode: [bold]{mode.value}[/] | Concurrent: [bold]{args.concurrent}[/]")
        console.print(f"  Cache: [bold]{'enabled' if not args.no_cache else 'disabled'}[/] | Workers: [bold]{evaluator.max_workers}[/]")
        console.print()
    except ImportError:
        print(f"  Dataset: {total} queries | Mode: {mode.value} | Concurrent: {args.concurrent}")
        print(f"  Cache: {'enabled' if not args.no_cache else 'disabled'} | Workers: {evaluator.max_workers}")
        print()

    # Run
    progress = RichProgress(total)
    progress.start()

    start_time = time.perf_counter()

    async def on_progress(current: int, stage: str = ""):
        await progress.update(current, stage)

    try:
        eval_results = await evaluator.run(progress_callback=on_progress)
    except KeyboardInterrupt:
        progress.stop()
        print("\n  Evaluation cancelled.")
        sys.exit(130)
    except Exception as e:
        progress.stop()
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        print(f"\n  ERROR: {e}")
        sys.exit(1)
    finally:
        await evaluator.teardown()

    progress.stop()
    elapsed = time.perf_counter() - start_time

    # Report
    print_terminal_report(eval_results)

    if args.show_detail > 0:
        print_per_query_detail(eval_results.get("per_query_results", []), args.show_detail)

    # Performance
    cached = eval_results.get("cached_count", 0)
    non_cached = total - cached
    per_query = elapsed / max(1, non_cached) if non_cached > 0 else 0

    try:
        from rich.console import Console
        console = Console()
        console.print(f"  Total time: [bold]{elapsed:.1f}s[/]")
        console.print(f"  Per query (non-cached): [bold]{per_query:.1f}s[/]")
        console.print(f"  Queries/sec: [bold]{total / elapsed:.1f}[/]")
        if cached:
            console.print(f"  Cache hits: [bold]{cached}/{total}[/]")
        console.print()
    except ImportError:
        print(f"  Total time: {elapsed:.1f}s")
        print(f"  Per query (non-cached): {per_query:.1f}s")
        print(f"  Queries/sec: {total / elapsed:.1f}")
        if cached:
            print(f"  Cache hits: {cached}/{total}")
        print()

    # Export
    try:
        from rich.console import Console
        console = Console()
        console.print("  [bold]Generating reports...[/]")
    except ImportError:
        print("  Generating reports...")

    json_path = save_json(eval_results)
    summary_path = save_summary_json(eval_results)
    csv_path = save_csv(eval_results)
    md_path = save_markdown(eval_results)

    print(f"    JSON:      {json_path}")
    print(f"    Summary:   {summary_path}")
    print(f"    CSV:       {csv_path}")
    print(f"    Markdown:  {md_path}")

    if not args.no_excel:
        try:
            xlsx_path = save_excel(eval_results)
            print(f"    Excel:     {xlsx_path}")
        except Exception as e:
            print(f"    Excel:     skipped ({e})")

    if not args.no_charts:
        try:
            chart_paths = save_charts(eval_results)
            for cp in chart_paths:
                print(f"    Chart:     {cp}")
        except Exception as e:
            print(f"    Charts:    skipped ({e})")

    print()
    print("  Evaluation complete!")
    print()


if __name__ == "__main__":
    asyncio.run(main())
