import asyncio
import csv
import json
import time
from pathlib import Path
from typing import Any

from app.agents.evidence_agent import EvidenceAgent
from app.agents.graph import AgenticGraph
from app.agents.supervisor import SupervisorAgent
from app.core.config import get_settings
from app.core.constants import ModelMode, Persona
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever
from app.services.ai.context_budget import estimate_tokens
from app.services.ai.model_gateway import ModelGateway
from app.services.external.http_client import ExternalHttpClient
from app.services.external.pubchem import PubChemTool
from app.services.external.pubmed import PubMedTool

QUERIES = [
    "senyawa di dalam kelor apa aja?",
    "senyawa aktif temulawak apa saja?",
    "manfaat kunyit apa?",
    "nama ilmiah jahe apa?",
    "analisis mekanisme molekuler kurkumin",
    "apa interaksi dan kontraindikasi jahe?",
]

FIELDS = [
    "query",
    "intent",
    "persona",
    "mode",
    "execution_mode_used",
    "direct_answer_used",
    "model_calls",
    "refinement_used",
    "retrieval_source",
    "estimated_input_tokens",
    "output_tokens",
    "retrieval_ms",
    "ttft_ms",
    "generation_ms",
    "refinement_ms",
    "persistence_ms",
    "total_ms",
    "tokens_per_second",
    "finish_reason",
    "error_code",
]


async def run_one(graph: AgenticGraph, query: str, persona: Persona, mode: ModelMode) -> dict[str, Any]:
    started = time.perf_counter()
    state: dict[str, Any] = {
        "user_query": query,
        "persona": persona.value,
        "model_mode": mode.value,
        "chat_history": [],
        "attachment_context": [],
        "timings": {"intent_ms": 0, "retrieval_ms": 0, "ttft_ms": 0, "generation_ms": 0, "persistence_ms": 0, "total_ms": 0},
    }
    base = {"query": query, "persona": persona.value, "mode": mode.value}
    try:
        result = await graph.run(state)  # type: ignore[arg-type]
        timings = result.get("timings", {})
        answer = result.get("grounded_answer") or result.get("draft_answer") or ""
        total_ms = timings.get("total_ms") or int((time.perf_counter() - started) * 1000)
        output_tokens = estimate_tokens(str(answer))
        generation_ms = timings.get("generation_ms", 0) or 0
        return {
            **base,
            "intent": result.get("query_intent") or result.get("intent"),
            "execution_mode_used": result.get("execution_mode_used"),
            "direct_answer_used": bool(result.get("direct_answer_used")),
            "model_calls": result.get("model_calls", result.get("model_call_count", 0)),
            "refinement_used": bool(result.get("refinement_used")),
            "retrieval_source": result.get("retrieval_source"),
            "estimated_input_tokens": estimate_tokens(query),
            "output_tokens": output_tokens,
            "retrieval_ms": timings.get("retrieval_ms", 0),
            "ttft_ms": timings.get("ttft_ms", 0),
            "generation_ms": generation_ms,
            "refinement_ms": timings.get("refinement_ms", 0),
            "persistence_ms": timings.get("persistence_ms", 0),
            "total_ms": total_ms,
            "tokens_per_second": round((output_tokens / (generation_ms / 1000)), 2) if generation_ms else 0,
            "finish_reason": result.get("finish_reason"),
            "error_code": result.get("error_code"),
        }
    except Exception as exc:
        return {
            **base,
            "intent": "",
            "execution_mode_used": "error",
            "direct_answer_used": False,
            "model_calls": 0,
            "refinement_used": False,
            "retrieval_source": None,
            "estimated_input_tokens": estimate_tokens(query),
            "output_tokens": 0,
            "retrieval_ms": 0,
            "ttft_ms": 0,
            "generation_ms": 0,
            "refinement_ms": 0,
            "persistence_ms": 0,
            "total_ms": int((time.perf_counter() - started) * 1000),
            "tokens_per_second": 0,
            "finish_reason": "error",
            "error_code": f"{type(exc).__name__}: {exc}",
        }


async def main() -> None:
    settings = get_settings()
    client = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(client)
    external = ExternalHttpClient()
    evidence = EvidenceAgent(PubMedTool(settings, external), PubChemTool(settings, external))
    graph = AgenticGraph(SupervisorAgent(evidence), GraphRetriever(repo), ModelGateway(settings))
    rows: list[dict[str, Any]] = []
    out_json = Path("docs/final_benchmark_after.json")
    out_csv = Path("docs/final_benchmark_after.csv")

    def flush() -> None:
        out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        with out_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    try:
        for query in QUERIES:
            for persona in Persona:
                for mode in ModelMode:
                    row = await run_one(graph, query, persona, mode)
                    rows.append(row)
                    flush()
                    print(json.dumps(row, ensure_ascii=False), flush=True)
    finally:
        await graph.gateway.close()
        await external.close()
        await client.close()
        flush()


if __name__ == "__main__":
    asyncio.run(main())
