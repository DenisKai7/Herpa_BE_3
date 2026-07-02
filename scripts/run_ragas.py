"""Standalone script to run Ragas evaluation without starting the FastAPI server.

Usage:
    python scripts/run_ragas.py
"""

import asyncio
import logging
import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.dependencies.services import create_services, close_services
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.evaluation.ragas_engine import DEFAULT_TEST_CASES, run_evaluation


async def main():
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger("ragas_runner")

    # If ragas is not installed, tell user first
    try:
        import ragas  # noqa: F401
        import datasets  # noqa: F401
    except ImportError:
        print("ERROR: Dependencies belum terinstall. Jalankan:")
        print("  pip install ragas datasets langchain-openai")
        sys.exit(1)

    print("=" * 60)
    print("HERPA — Ragas GraphRAG Evaluation Runner")
    print("=" * 60)
    print(f"LLM endpoint : {settings.llama_text_base_url}")
    print(f"LLM model    : {settings.llama_text_model_name}")
    print(f"Test cases   : {len(DEFAULT_TEST_CASES)}")
    print()

    # Initialize services
    services = await create_services(settings)
    try:
        result = await run_evaluation(services, DEFAULT_TEST_CASES)

        print()
        print("=" * 60)
        print("HASIL EVALUASI")
        print("=" * 60)

        if result.error:
            print(f"ERROR: {result.error}")
        else:
            print(f"Waktu       : {result.elapsed_seconds}s")
            print(f"Test cases  : {result.test_case_count}")
            print()
            print("METRIK KESELURUHAN:")
            print("-" * 40)
            for metric, value in result.overall_metrics.items():
                if isinstance(value, float):
                    print(f"  {metric:<25} : {value:.4f}")
                else:
                    print(f"  {metric:<25} : {value}")

            print()
            print("DETAIL PER TEST CASE:")
            print("-" * 40)
            for i, case in enumerate(result.per_test_case, 1):
                print(f"\n[{i}] Q: {case['question']}")
                print(f"    Answer : {case['answer'][:120]}...")
                print(f"    Contexts: {len(case['contexts'])} retrieved")
                if "metrics" in case:
                    for k, v in case["metrics"].items():
                        if isinstance(v, float):
                            print(f"    {k}: {v:.4f}")

            if result.csv_path:
                print(f"\nCSV saved  : {result.csv_path}")

    finally:
        await close_services(services)

    print()
    print("Selesai.")


if __name__ == "__main__":
    asyncio.run(main())
