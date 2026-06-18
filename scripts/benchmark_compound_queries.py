import asyncio
import csv
import json
import time
from pathlib import Path
from typing import Any

from app.agents.graph import AgenticGraph
from app.agents.supervisor import SupervisorAgent
from app.core.config import get_settings
from app.core.constants import ModelMode, Persona
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever
from app.services.ai.model_gateway import ModelGateway

QUESTIONS = [
    "senyawa di dalam kelor apa aja?",
    "senyawa aktif temulawak apa saja?",
    "kandungan kimia kunyit apa?",
    "senyawa utama jahe apa?",
]

FIELDS = [
    "question",
    "intent",
    "persona",
    "mode",
    "direct_answer_used",
    "model_calls",
    "retrieval_ms",
    "ttft_ms",
    "generation_ms",
    "total_ms",
    "compound_count",
    "answer_length",
    "finish_reason",
    "error",
]


async def run_one(graph: AgenticGraph, question: str, persona: Persona, mode: ModelMode) -> dict[str, Any]:
    started = time.perf_counter()
    state: dict[str, Any] = {
        "user_query": question,
        "persona": persona.value,
        "model_mode": mode.value,
        "chat_history": [],
        "attachment_context": [],
    }
    row: dict[str, Any] = {"question": question, "persona": persona.value, "mode": mode.value, "error": ""}
    try:
        result = await graph.run(state)  # type: ignore[arg-type]
        timings = result.get("timings", {})
        answer = result.get("grounded_answer") or result.get("draft_answer") or ""
        row.update(
            {
                "intent": result.get("query_intent") or result.get("intent"),
                "direct_answer_used": bool(result.get("direct_answer_used")),
                "model_calls": result.get("model_calls", result.get("model_call_count", 0)),
                "retrieval_ms": timings.get("retrieval_ms", 0),
                "ttft_ms": timings.get("ttft_ms", 0),
                "generation_ms": timings.get("generation_ms", 0),
                "total_ms": timings.get("total_ms", int((time.perf_counter() - started) * 1000)),
                "compound_count": result.get("compound_count", 0),
                "answer_length": len(answer),
                "finish_reason": result.get("finish_reason"),
            }
        )
    except Exception as exc:  # benchmark must record real failures, not hide them
        row.update(
            {
                "intent": "",
                "direct_answer_used": False,
                "model_calls": 0,
                "retrieval_ms": 0,
                "ttft_ms": 0,
                "generation_ms": 0,
                "total_ms": int((time.perf_counter() - started) * 1000),
                "compound_count": 0,
                "answer_length": 0,
                "finish_reason": "error",
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    return row


async def main() -> None:
    settings = get_settings()
    client = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(client)
    retriever = GraphRetriever(repo)
    gateway = ModelGateway(settings)
    graph = AgenticGraph(SupervisorAgent(settings), retriever, gateway)
    rows: list[dict[str, Any]] = []
    out_dir = Path("benchmarks")
    out_dir.mkdir(exist_ok=True)
    json_path = out_dir / "compound_queries_latest.json"
    csv_path = out_dir / "compound_queries_latest.csv"

    def flush() -> None:
        json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    try:
        for question in QUESTIONS:
            for persona in Persona:
                for mode in ModelMode:
                    row = await run_one(graph, question, persona, mode)
                    rows.append(row)
                    flush()
                    print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        await gateway.close()
        await client.close()
        flush()

    print(json.dumps({"rows": len(rows), "json": str(json_path), "csv": str(csv_path)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
