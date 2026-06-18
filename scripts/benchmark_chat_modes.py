from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

from app.core.config import get_settings  # noqa: E402
from app.core.model_modes import normalize_model_mode, normalize_persona  # noqa: E402
from app.graph.neo4j_client import Neo4jClient  # noqa: E402
from app.graph.repositories import KnowledgeGraphRepository  # noqa: E402
from app.graph.retriever import GraphRetriever  # noqa: E402

QUESTIONS = [
    "Senyawa aktif di temulawak apa saja?",
    "Jelaskan manfaat kunyit.",
    "Analisis mekanisme molekuler kurkumin.",
    "Apa interaksi dan kontraindikasi jahe?",
]
PERSONAS = ["umum", "pelajar", "peneliti", "tenaga_medis"]
MODES = ["fast-medium", "thinking-high"]


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--include-model", action="store_true", help="Reserved for authenticated chat/model benchmark"
    )
    args = parser.parse_args()

    settings = get_settings()
    client = Neo4jClient(settings)
    repository = KnowledgeGraphRepository(client)
    retriever = GraphRetriever(repository)
    results: list[dict[str, Any]] = []
    started_all = time.perf_counter()
    try:
        for question in QUESTIONS:
            for persona_raw in PERSONAS:
                for mode_raw in MODES:
                    persona = normalize_persona(persona_raw).value
                    mode = normalize_model_mode(mode_raw).value
                    started = time.perf_counter()
                    error = None
                    facts = []
                    try:
                        retrieval = await retriever.retrieve(
                            question, limit=1 if mode == "fast-medium" else 2
                        )
                        facts = retrieval.get("facts", [])
                    except Exception as exc:
                        error = f"{type(exc).__name__}: {str(exc)[:300]}"
                    total_ms = int((time.perf_counter() - started) * 1000)
                    results.append(
                        {
                            "question": question,
                            "persona": persona,
                            "mode": mode,
                            "retrieval_ms": total_ms,
                            "total_latency_ms": total_ms,
                            "ttft_ms": None,
                            "prompt_tokens": None,
                            "output_tokens": None,
                            "tokens_per_second": None,
                            "model_call_count": 0,
                            "refinement_used": False,
                            "response_length": 0,
                            "retrieval_items": len(facts),
                            "compound_count": sum(
                                len(row.get("compounds", [])) for row in facts if isinstance(row, dict)
                            ),
                            "error": error,
                        }
                    )
    finally:
        await client.close()

    payload = {
        "benchmark_type": "retrieval_baseline" if not args.include_model else "chat_model_requested",
        "note": "No Supabase bearer token is used; this measures GraphRAG retrieval path only.",
        "total_ms": int((time.perf_counter() - started_all) * 1000),
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if any(item["error"] for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
