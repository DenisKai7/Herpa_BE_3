"""HERPA GraphRAG Evaluation Orchestrator v3 — Fully Optimized.

Optimizations vs v2:
  1. Combined LLM judge: 1 call instead of 6 (batch_judge.py)
  2. Disk cache: pickle-based, covers retrieval, answers, judge results
  3. ThreadPoolExecutor: pure-Python metrics run in parallel across queries
  4. Quick mode: 20 queries, skip hallucination/citation details
  5. Batch processing: concurrent queries with semaphore
  6. Profiling: per-stage timing breakdown
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from app.agents.evidence_agent import EvidenceAgent
from app.agents.graph import AgenticGraph
from app.agents.state import AgentState
from app.agents.supervisor import SupervisorAgent
from app.core.config import Settings, get_settings
from app.graph.context_builder import format_herb_fact
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever
from app.services.ai.model_gateway import ModelGateway
from app.services.external.http_client import ExternalHttpClient
from app.services.external.pubchem import PubChemTool
from app.services.external.pubmed import PubMedTool

from evaluation.metrics.batch_judge import JudgeResult, evaluate_combined
from evaluation.metrics.citation import compute_citation_accuracy, aggregate_citation_metrics
from evaluation.metrics.graph_metrics import compute_graph_accuracy, aggregate_graph_metrics
from evaluation.metrics.latency import aggregate_latency
from evaluation.metrics.retrieval_metrics import compute_retrieval_metrics, aggregate_retrieval_metrics

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).parent / "datasets"
CACHE_DIR = Path(__file__).parent / "cache"


# ─── Evaluation Mode ─────────────────────────────────────────────────────────

class EvalMode(str, Enum):
    QUICK = "quick"       # 10 queries, 4 DeepEval metrics, <3 min
    STANDARD = "standard" # 30 queries, all metrics, <10 min
    FULL = "full"         # 100 queries, all metrics, final research


# ─── Cache ───────────────────────────────────────────────────────────────────

class DiskCache:
    """Pickle-based disk cache for evaluation intermediate results."""

    def __init__(self, name: str):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._path = CACHE_DIR / f"{name}.pkl"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "rb") as f:
                    self._data = pickle.load(f)
            except Exception:
                self._data = {}

    def save(self):
        with open(self._path, "wb") as f:
            pickle.dump(self._data, f, protocol=pickle.HIGHEST_PROTOCOL)

    def get(self, key: str) -> Any | None:
        return self._data.get(key)

    def put(self, key: str, value: Any):
        self._data[key] = value

    def has(self, key: str) -> bool:
        return key in self._data

    def clear(self):
        self._data.clear()
        if self._path.exists():
            self._path.unlink(missing_ok=True)

    def __len__(self):
        return len(self._data)


def _cache_key(query: str, **kwargs) -> str:
    """Generate cache key from query and optional parameters."""
    parts = [query] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


# ─── Profiler ────────────────────────────────────────────────────────────────

class Profiler:
    """Simple stage profiler."""

    def __init__(self):
        self.stages: dict[str, float] = {}
        self._current_stage: str = ""
        self._current_start: float = 0.0

    def start(self, stage: str):
        if self._current_stage:
            self.stop()
        self._current_stage = stage
        self._current_start = time.perf_counter()

    def stop(self):
        if self._current_stage:
            elapsed = time.perf_counter() - self._current_start
            self.stages[self._current_stage] = self.stages.get(self._current_stage, 0) + elapsed
            self._current_stage = ""

    def finish(self):
        self.stop()

    def report(self) -> dict[str, float]:
        return dict(self.stages)

    def total(self) -> float:
        return sum(self.stages.values())


# ─── Evaluator ───────────────────────────────────────────────────────────────

class Evaluator:
    """Optimized evaluation orchestrator v3."""

    def __init__(
        self,
        settings: Settings | None = None,
        max_concurrent: int = 5,
        mode: EvalMode = EvalMode.FULL,
        use_cache: bool = True,
        clear_cache: bool = False,
        max_workers: int = 0,
    ):
        self.settings = settings or get_settings()
        self.max_concurrent = max_concurrent
        self.mode = mode
        self.use_cache = use_cache
        self.profiler = Profiler()

        # Thread pool for pure-Python metrics
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        # Caches
        if clear_cache:
            for name in ["retrieval", "answer", "judge", "results"]:
                DiskCache(name).clear()
        self._retrieval_cache = DiskCache("retrieval")
        self._answer_cache = DiskCache("answer")
        self._judge_cache = DiskCache("judge")
        self._results_cache = DiskCache("results")

        # Services
        self.neo4j_client: Neo4jClient | None = None
        self.graph_repo: KnowledgeGraphRepository | None = None
        self.retriever: GraphRetriever | None = None
        self.agent_graph: AgenticGraph | None = None
        self.llm_client: AsyncOpenAI | None = None
        self.external: ExternalHttpClient | None = None

        # Datasets
        self.test_queries: list[dict] = []
        self.ground_truth_map: dict[int, dict] = {}

        # Results
        self.results: list[dict[str, Any]] = []

    async def setup(self):
        """Initialize services."""
        self.profiler.start("setup")

        # Load dataset based on mode
        dataset_files = {
            EvalMode.QUICK: "quick_questions.json",
            EvalMode.STANDARD: "standard_questions.json",
            EvalMode.FULL: "full_questions.json",
        }
        dataset_file = dataset_files[self.mode]
        dataset_path = DATASETS_DIR / dataset_file

        # Fallback to test_queries.json if mode-specific file doesn't exist
        if not dataset_path.exists():
            dataset_path = DATASETS_DIR / "test_queries.json"
            logger.warning(f"Dataset {dataset_file} not found, falling back to test_queries.json")

        with open(dataset_path, "r", encoding="utf-8") as f:
            self.test_queries = json.load(f)

        # For FULL mode, also try test_queries.json as the complete dataset
        if self.mode == EvalMode.FULL and dataset_file == "full_questions.json":
            fallback = DATASETS_DIR / "test_queries.json"
            if fallback.exists() and len(self.test_queries) < 50:
                with open(fallback, "r", encoding="utf-8") as f:
                    self.test_queries = json.load(f)

        with open(DATASETS_DIR / "ground_truth.json", "r", encoding="utf-8") as f:
            gt = json.load(f)
        self.ground_truth_map = {g["id"]: g for g in gt}

        # Init services
        self.neo4j_client = Neo4jClient(self.settings)
        self.graph_repo = KnowledgeGraphRepository(self.neo4j_client)
        self.retriever = GraphRetriever(self.graph_repo)

        self.llm_client = AsyncOpenAI(
            base_url=self.settings.llama_text_base_url,
            api_key="not-needed",
        )

        self.external = ExternalHttpClient()
        pubmed = PubMedTool(self.settings, self.external)
        pubchem = PubChemTool(self.settings, self.external)
        evidence = EvidenceAgent(pubmed, pubchem)
        supervisor = SupervisorAgent(evidence)
        gateway = ModelGateway(self.settings)
        self.agent_graph = AgenticGraph(supervisor, self.retriever, gateway)

        self.profiler.stop()
        logger.info(f"Setup done: {len(self.test_queries)} queries, mode={self.mode.value}")

    async def teardown(self):
        """Cleanup."""
        self._executor.shutdown(wait=False)
        # Save caches
        self._retrieval_cache.save()
        self._answer_cache.save()
        self._judge_cache.save()
        self._results_cache.save()
        if self.neo4j_client:
            await self.neo4j_client.close()
        if self.external:
            try:
                await self.external.close()
            except Exception:
                pass

    # ─── Pipeline stages ─────────────────────────────────────────────────────

    async def _retrieve(self, query: str, query_id: int) -> dict[str, Any]:
        """Retrieve from graph. Cached."""
        ck = _cache_key(query, stage="retrieval")
        cached = self._retrieval_cache.get(ck)
        if cached is not None:
            return cached

        t0 = time.perf_counter()
        try:
            retrieval = await self.retriever.retrieve(query, limit=5, cache_ttl=300)
        except Exception as e:
            logger.warning(f"Retrieval failed for Q{query_id}: {e}")
            retrieval = {"entities": [], "facts": [], "grounding_status": "error"}
        retrieval["_latency_ms"] = (time.perf_counter() - t0) * 1000

        self._retrieval_cache.put(ck, retrieval)
        return retrieval

    def _build_contexts(self, retrieval: dict) -> list[str]:
        """Extract context strings from retrieval result."""
        contexts = []
        for fact in retrieval.get("facts", []):
            text = format_herb_fact(fact)
            if text.strip():
                contexts.append(text)
        return contexts

    def _extract_nodes(self, retrieval: dict) -> list[str]:
        """Extract retrieved node names."""
        nodes = []
        for entity in retrieval.get("entities", []):
            name = entity.get("canonical_name") or entity.get("original_text", "")
            if name:
                nodes.append(name)
        for fact in retrieval.get("facts", []):
            plant = fact.get("plant", {})
            if plant.get("scientific_name"):
                nodes.append(plant["scientific_name"])
            if plant.get("local_name"):
                nodes.append(plant["local_name"])
            for compound in fact.get("compounds", []):
                if isinstance(compound, dict) and compound.get("name"):
                    nodes.append(compound["name"])
        return nodes

    async def _generate_answer(self, query: str, query_id: int) -> dict[str, Any]:
        """Run agent pipeline. Cached."""
        ck = _cache_key(query, stage="answer")
        cached = self._answer_cache.get(ck)
        if cached is not None:
            return cached

        state: AgentState = {
            "request_id": f"eval-{query_id}",
            "user_id": "eval-system",
            "application_role": "user",
            "persona": "umum",
            "model_mode": "fast-medium",
            "requested_mode": "fast-medium",
            "execution_mode_used": "fast-medium",
            "chat_id": None,
            "user_query": query,
            "attachment_ids": [],
            "attachment_context": [],
            "errors": [],
            "timings": {"auth_ms": 0, "profile_ms": 0, "retrieval_ms": 0, "ttft_ms": 0, "generation_ms": 0, "persistence_ms": 0, "total_ms": 0},
        }

        t0 = time.perf_counter()
        try:
            state = await self.agent_graph.run(state)
        except Exception as e:
            logger.warning(f"Agent failed for Q{query_id}: {e}")
            state["errors"] = [{"error": str(e)}]
        agent_ms = (time.perf_counter() - t0) * 1000

        result = {
            "answer": state.get("grounded_answer") or state.get("draft_answer") or "",
            "timings": state.get("timings", {}),
            "citations": state.get("citations", []),
            "agent_latency_ms": agent_ms,
        }

        self._answer_cache.put(ck, result)
        return result

    async def _judge(self, query: str, answer: str, contexts: list[str], ground_truth: str) -> JudgeResult:
        """Combined LLM judge. Cached."""
        ck = _cache_key(query, answer=answer[:200], stage="judge")
        cached = self._judge_cache.get(ck)
        if cached is not None:
            return cached

        result = await evaluate_combined(
            self.llm_client,
            self.settings.llama_text_model_name,
            query, answer, contexts, ground_truth,
        )

        # Cache as dict for pickle compatibility
        result_dict = {
            "answer_relevancy": result.answer_relevancy,
            "faithfulness": result.faithfulness,
            "contextual_precision": result.contextual_precision,
            "contextual_recall": result.contextual_recall,
            "contextual_relevancy": result.contextual_relevancy,
            "hallucination_score": result.hallucination_score,
            "success": result.success,
            "error": result.error,
            "latency_ms": result.latency_ms,
        }
        self._judge_cache.put(ck, result_dict)
        return result

    def _compute_manual_metrics(
        self,
        retrieved_nodes: list[str],
        retrieval: dict,
        answer: str,
        contexts: list[str],
        expected_nodes: list[str],
        expected_rels: list[str],
        key_facts: list[str],
    ) -> dict[str, Any]:
        """Compute all pure-Python metrics (no I/O)."""
        retrieval_metrics = compute_retrieval_metrics(retrieved_nodes, expected_nodes, key_facts)
        graph_accuracy = compute_graph_accuracy(retrieval, expected_nodes, expected_rels)

        citation_metrics = {"correct": 0, "incorrect": 0, "missing": 0, "accuracy": 1.0, "details": []}
        if self.mode == EvalMode.FULL:
            citation_metrics = compute_citation_accuracy(answer, retrieval, contexts)

        return {
            "retrieval_metrics": retrieval_metrics,
            "graph_accuracy": graph_accuracy,
            "citation_metrics": citation_metrics,
        }

    # ─── Single query ────────────────────────────────────────────────────────

    async def _evaluate_single(self, query_data: dict, index: int, progress_cb=None) -> dict[str, Any]:
        """Full evaluation for one query."""
        query_id = query_data["id"]
        query = query_data["query"]
        gt = self.ground_truth_map.get(query_id, {})

        # Check full result cache
        ck = _cache_key(query, mode=self.mode.value)
        cached = self._results_cache.get(ck)
        if cached is not None:
            cached["_from_cache"] = True
            if progress_cb:
                await progress_cb(index + 1, "cached")
            return cached

        # ── Stage 1: Retrieve ─────────────────────────────────────────
        if progress_cb:
            await progress_cb(index + 1, "retrieving")
        retrieval = await self._retrieve(query, query_id)
        contexts = self._build_contexts(retrieval)
        retrieved_nodes = self._extract_nodes(retrieval)

        # ── Stage 2: Generate Answer ──────────────────────────────────
        if progress_cb:
            await progress_cb(index + 1, "generating")
        answer_data = await self._generate_answer(query, query_id)
        answer = answer_data["answer"]

        # ── Stage 3: Manual Metrics (parallel via thread pool) ────────
        if progress_cb:
            await progress_cb(index + 1, "metrics")
        expected_nodes = gt.get("expected_nodes", [])
        expected_rels = gt.get("expected_relationships", [])
        key_facts = gt.get("key_facts", [])

        loop = asyncio.get_event_loop()
        manual = await loop.run_in_executor(
            self._executor,
            self._compute_manual_metrics,
            retrieved_nodes, retrieval, answer, contexts,
            expected_nodes, expected_rels, key_facts,
        )

        # ── Stage 4: LLM Judge (1 combined call) ─────────────────────
        if progress_cb:
            await progress_cb(index + 1, "judging")
        judge = await self._judge(
            query, answer, contexts, gt.get("expected_answer", ""),
        )

        # ── Assemble result ───────────────────────────────────────────
        retrieval_ms = retrieval.get("_latency_ms", 0)
        timings = answer_data.get("timings", {})
        agent_ms = answer_data.get("agent_latency_ms", 0)

        result = {
            "id": query_id,
            "query": query,
            "category": query_data.get("category", "unknown"),
            "answer": answer,
            "ground_truth": gt.get("expected_answer", ""),
            "contexts": contexts,
            "retrieved_nodes": retrieved_nodes,
            "expected_nodes": expected_nodes,
            "expected_relationships": expected_rels,

            # Manual metrics
            **manual,

            # Judge metrics
            "answer_relevancy": judge.get("answer_relevancy", 0.0) if isinstance(judge, dict) else judge.answer_relevancy,
            "faithfulness": judge.get("faithfulness", 0.0) if isinstance(judge, dict) else judge.faithfulness,
            "contextual_precision": judge.get("contextual_precision", 0.0) if isinstance(judge, dict) else judge.contextual_precision,
            "contextual_recall": judge.get("contextual_recall", 0.0) if isinstance(judge, dict) else judge.contextual_recall,
            "contextual_relevancy": judge.get("contextual_relevancy", 0.0) if isinstance(judge, dict) else judge.contextual_relevancy,
            "hallucination_score": judge.get("hallucination_score", 0.0) if isinstance(judge, dict) else judge.hallucination_score,
            "judge_success": judge.get("success", True) if isinstance(judge, dict) else judge.success,
            "judge_latency_ms": judge.get("latency_ms", 0) if isinstance(judge, dict) else judge.latency_ms,

            # Latency
            "latency": {
                "retrieval_ms": retrieval_ms,
                "agent_ms": agent_ms,
                "neo4j_ms": timings.get("retrieval_ms", 0),
                "llm_ms": timings.get("generation_ms", 0),
                "judge_ms": judge.get("latency_ms", 0) if isinstance(judge, dict) else judge.latency_ms,
                "total_ms": agent_ms + (judge.get("latency_ms", 0) if isinstance(judge, dict) else judge.latency_ms),
            },
        }

        # Cache result
        self._results_cache.put(ck, result)

        if progress_cb:
            await progress_cb(index + 1, "done")

        return result

    # ─── Batch runner ────────────────────────────────────────────────────────

    async def run(self, progress_callback=None) -> dict[str, Any]:
        """Run evaluation with concurrency control."""
        total = len(self.test_queries)
        self.results = []
        self.profiler.start("evaluation")

        semaphore = asyncio.Semaphore(self.max_concurrent)
        lock = asyncio.Lock()

        async def _run_one(qd, idx):
            async with semaphore:
                result = await self._evaluate_single(qd, idx, progress_callback)
                async with lock:
                    self.results.append(result)
                return result

        tasks = [_run_one(qd, i) for i, qd in enumerate(self.test_queries)]
        await asyncio.gather(*tasks, return_exceptions=True)

        self.profiler.stop()

        # Sort by id
        self.results.sort(key=lambda r: r.get("id", 0))

        # Save caches
        self._retrieval_cache.save()
        self._answer_cache.save()
        self._judge_cache.save()
        self._results_cache.save()

        cached_count = sum(1 for r in self.results if r.get("_from_cache"))

        aggregated = self._aggregate_all()
        return {
            "total_queries": total,
            "cached_count": cached_count,
            "mode": self.mode.value,
            "aggregated_metrics": aggregated,
            "per_query_results": self.results,
            "profiling": self.profiler.report(),
            "total_profiling_s": self.profiler.total(),
        }

    def _aggregate_all(self) -> dict[str, Any]:
        """Aggregate all metrics."""
        if not self.results:
            return {}

        # Retrieval (manual)
        all_retrieval = [r.get("retrieval_metrics", {}) for r in self.results]
        retrieval_agg = aggregate_retrieval_metrics(all_retrieval)

        # Judge metrics (averages)
        judge_keys = [
            "answer_relevancy", "faithfulness", "contextual_precision",
            "contextual_recall", "contextual_relevancy", "hallucination_score",
        ]
        judge_agg = {}
        for key in judge_keys:
            vals = [r.get(key, 0.0) for r in self.results if r.get(key) is not None]
            judge_agg[key] = round(sum(vals) / len(vals), 4) if vals else 0.0

        # Citation
        all_citation = [r.get("citation_metrics", {}) for r in self.results]
        citation_agg = aggregate_citation_metrics(all_citation)

        # Graph
        all_graph = [r.get("graph_accuracy", {}) for r in self.results]
        graph_agg = aggregate_graph_metrics(all_graph)

        # Latency
        all_latency = [r.get("latency", {}) for r in self.results]
        latency_agg = aggregate_latency(all_latency)

        # Overall
        overall = self._compute_overall(retrieval_agg, judge_agg, citation_agg, graph_agg)

        return {
            "retrieval": retrieval_agg,
            "judge": judge_agg,
            "citation": citation_agg,
            "graph": graph_agg,
            "latency": latency_agg,
            "overall_score": overall,
        }

    def _compute_overall(self, retrieval, judge, citation, graph) -> dict[str, Any]:
        weights = {
            "retrieval": 0.15, "answer_relevancy": 0.15, "faithfulness": 0.15,
            "contextual_precision": 0.10, "contextual_recall": 0.10,
            "contextual_relevancy": 0.10, "hallucination": 0.05,
            "citation": 0.10, "graph": 0.10,
        }
        scores = {
            "retrieval": retrieval.get("ndcg", 0.0) * 100,
            "answer_relevancy": judge.get("answer_relevancy", 0.0) * 100,
            "faithfulness": judge.get("faithfulness", 0.0) * 100,
            "contextual_precision": judge.get("contextual_precision", 0.0) * 100,
            "contextual_recall": judge.get("contextual_recall", 0.0) * 100,
            "contextual_relevancy": judge.get("contextual_relevancy", 0.0) * 100,
            "hallucination": judge.get("hallucination_score", 0.0) * 100,
            "citation": citation.get("accuracy", 0.0) * 100,
            "graph": graph.get("overall_accuracy", 0.0) * 100,
        }
        total_score = round(sum(scores[k] * weights[k] for k in weights), 2)

        if total_score >= 95: grade = "A+"
        elif total_score >= 90: grade = "A"
        elif total_score >= 85: grade = "A-"
        elif total_score >= 80: grade = "B+"
        elif total_score >= 75: grade = "B"
        elif total_score >= 70: grade = "B-"
        elif total_score >= 65: grade = "C+"
        elif total_score >= 60: grade = "C"
        else: grade = "D"

        return {"score": total_score, "grade": grade, "component_scores": scores, "weights": weights}
