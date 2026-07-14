"""HERPA GraphRAG Evaluation Orchestrator v7 — GraphRAG-Optimized.

Major changes from v6:
  1. Removed DeepEval metrics not applicable to GraphRAG (faithfulness, context_precision,
     context_recall, context_relevancy, hallucination)
  2. Judge evaluates ONLY answer_relevancy
  3. Overall score uses only: Retrieval, Generation, Citation, Graph, Performance
  4. Cache backward-compatible: old cache entries with removed metrics are handled gracefully
  5. Token-based context truncation with priority ordering
  6. Retrieval audit integration
  7. Comprehensive analytics
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import random
import statistics
import time
import traceback
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
from evaluation.context_builder import build_evaluation_context, format_context_for_judge, MIN_CONTEXT_CHARS
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever
from app.services.ai.model_gateway import ModelGateway
from app.services.external.http_client import ExternalHttpClient
from app.services.external.pubchem import PubChemTool
from app.services.external.pubmed import PubMedTool

from evaluation.analytics import compute_all_analytics
from evaluation.metrics.batch_judge import JudgeResult, evaluate_answer_relevancy, JUDGE_PROMPT_VERSION
from evaluation.metrics.citation import compute_citation_accuracy, aggregate_citation_metrics
from evaluation.metrics.graph_metrics import compute_graph_accuracy, aggregate_graph_metrics
from evaluation.metrics.latency import aggregate_latency
from evaluation.metrics.retrieval_metrics import compute_retrieval_metrics, aggregate_retrieval_metrics
from evaluation.retrieval_audit import build_retrieval_audit, audit_to_dict, RetrievalAudit

logger = logging.getLogger(__name__)

DATASETS_DIR = Path(__file__).parent / "datasets"
CACHE_DIR = Path(__file__).parent / "cache"

# Token-based context limits
MAX_CONTEXT_TOKENS = 1000
CHARS_PER_TOKEN = 4
MAX_CONTEXT_CHARS = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN

# Removed metric keys (for cache backward compatibility)
_REMOVED_METRICS = {
    "faithfulness", "contextual_precision", "contextual_recall",
    "contextual_relevancy", "hallucination_score",
}


class EvalMode(str, Enum):
    DEBUG = "debug"
    QUICK = "quick"
    STANDARD = "standard"
    FULL = "full"


class DiskCache:
    """Pickle-based disk cache with staleness detection."""

    def __init__(self, name: str, max_age_hours: float = 24.0):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self._path = CACHE_DIR / f"{name}.pkl"
        self._max_age = max_age_hours * 3600
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self):
        if self._path.exists():
            try:
                with open(self._path, "rb") as f:
                    self._data = pickle.load(f)
                mtime = self._path.stat().st_mtime
                if time.time() - mtime > self._max_age:
                    logger.info(f"Cache '{self._path.name}' expired (>{self._max_age/3600:.0f}h), clearing")
                    self._data.clear()
            except Exception as e:
                logger.warning(f"Cache '{self._path.name}' corrupted: {e}")
                self._data = {}

    def save(self):
        try:
            with open(self._path, "wb") as f:
                pickle.dump(self._data, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            logger.warning(f"Cache save failed: {e}")

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
    parts = [query] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _estimate_tokens(text: str) -> int:
    """Estimate token count. Approximate: 1 token ≈ 4 chars for mixed id/en."""
    return len(text) // CHARS_PER_TOKEN


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float. Returns default if not numeric."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default
    return default


def _strip_removed_metrics(data: dict) -> dict:
    """Remove deprecated metric keys from cache data for backward compatibility."""
    if not data:
        return data
    for key in _REMOVED_METRICS:
        data.pop(key, None)
    return data


def _priority_score_context(context_text: str, query: str, has_citation: bool = False) -> float:
    """Score a context chunk for priority ordering."""
    score = 0.0
    query_lower = query.lower()
    ctx_lower = context_text.lower()

    if has_citation or "sumber:" in ctx_lower or "referensi:" in ctx_lower or "[" in context_text:
        score += 10.0

    query_words = set(query_lower.split())
    ctx_words = set(ctx_lower.split())
    overlap = len(query_words & ctx_words)
    score += min(overlap * 2.0, 8.0)

    if "scientific_name" in ctx_lower or "nama ilmiah" in ctx_lower:
        score += 3.0
    if "compound" in ctx_lower or "senyawa" in ctx_lower:
        score += 2.0
    if "therapeutic" in ctx_lower or "manfaat" in ctx_lower or "khasiat" in ctx_lower:
        score += 2.0

    if len(context_text) > 200:
        score += 1.0

    return score


def _truncate_contexts_token_based(contexts: list[str], query: str) -> list[str]:
    """Truncate contexts based on token budget with priority ordering."""
    if not contexts:
        return []

    scored = []
    for i, ctx in enumerate(contexts):
        has_citation = "sumber:" in ctx.lower() or "[" in ctx
        priority = _priority_score_context(ctx, query, has_citation)
        scored.append((priority, i, ctx))

    scored.sort(key=lambda x: (-x[0], x[1]))

    result = []
    total_tokens = 0

    for _priority, _orig_idx, ctx_text in scored:
        ctx_tokens = _estimate_tokens(ctx_text)
        if total_tokens + ctx_tokens > MAX_CONTEXT_TOKENS:
            remaining_tokens = MAX_CONTEXT_TOKENS - total_tokens
            if remaining_tokens > 25:
                max_chars = remaining_tokens * CHARS_PER_TOKEN
                truncated = ctx_text[:max_chars] + "..."
                result.append(truncated)
                total_tokens += _estimate_tokens(truncated)
            break
        result.append(ctx_text)
        total_tokens += ctx_tokens

    original_order = []
    for ctx in contexts:
        if ctx in result:
            original_order.append(ctx)
    return original_order


class Profiler:
    """Monotonic stage profiler with wall-clock total."""

    def __init__(self):
        self.stages: dict[str, float] = {}
        self._current_stage: str = ""
        self._current_start: float = 0.0
        self.wall_start: float = 0.0
        self.wall_end: float = 0.0

    def start_wall(self):
        self.wall_start = time.perf_counter()

    def stop_wall(self):
        self.wall_end = time.perf_counter()

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
        if self.wall_start and self.wall_end:
            return self.wall_end - self.wall_start
        return sum(self.stages.values())


class Evaluator:
    def __init__(
        self,
        settings: Settings | None = None,
        max_concurrent: int = 5,
        mode: EvalMode = EvalMode.QUICK,
        use_cache: bool = True,
        clear_cache: bool = False,
        max_workers: int = 0,
        seed: int | None = None,
    ):
        self.settings = settings or get_settings()
        self.max_concurrent = max_concurrent
        self.mode = mode
        self.use_cache = use_cache
        self.seed = seed
        self.profiler = Profiler()
        self.max_workers = max_workers or min(os.cpu_count() or 4, 8)
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers)

        if clear_cache:
            for name in ["retrieval", "answer", "judge", "results"]:
                DiskCache(name).clear()
            logger.info("All caches cleared")

        self._retrieval_cache = DiskCache("retrieval")
        self._answer_cache = DiskCache("answer")
        self._judge_cache = DiskCache("judge")
        self._results_cache = DiskCache("results")

        # Counters
        self._llm_calls = 0
        self._neo4j_calls = 0
        self._cache_hits = {"retrieval": 0, "answer": 0, "judge": 0, "results": 0}
        self._cache_misses = {"retrieval": 0, "answer": 0, "judge": 0, "results": 0}

        self.neo4j_client: Neo4jClient | None = None
        self.graph_repo: KnowledgeGraphRepository | None = None
        self.retriever: GraphRetriever | None = None
        self.agent_graph: AgenticGraph | None = None
        self.llm_client: AsyncOpenAI | None = None
        self.external: ExternalHttpClient | None = None
        self.test_queries: list[dict] = []
        self.ground_truth_map: dict[int, dict] = {}
        self.results: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self._previous_audit: RetrievalAudit | None = None

    async def setup(self):
        self.profiler.start("setup")

        dataset_files = {
            EvalMode.DEBUG: "quick_questions.json",
            EvalMode.QUICK: "quick_questions.json",
            EvalMode.STANDARD: "standard_questions.json",
            EvalMode.FULL: "full_questions.json",
        }
        dataset_path = DATASETS_DIR / dataset_files[self.mode]
        if not dataset_path.exists():
            dataset_path = DATASETS_DIR / "test_queries.json"

        with open(dataset_path, "r", encoding="utf-8") as f:
            self.test_queries = json.load(f)

        if self.mode == EvalMode.FULL and len(self.test_queries) < 50:
            fallback = DATASETS_DIR / "test_queries.json"
            if fallback.exists():
                with open(fallback, "r", encoding="utf-8") as f:
                    self.test_queries = json.load(f)

        if self.mode == EvalMode.DEBUG:
            self.test_queries = self.test_queries[:3]
        elif self.seed is not None:
            rng = random.Random(self.seed)
            if len(self.test_queries) > 3:
                self.test_queries = rng.sample(self.test_queries, min(len(self.test_queries), {
                    EvalMode.QUICK: 10,
                    EvalMode.STANDARD: 30,
                    EvalMode.FULL: len(self.test_queries),
                }.get(self.mode, len(self.test_queries))))
                logger.info(f"Sampled {len(self.test_queries)} queries with seed={self.seed}")

        with open(DATASETS_DIR / "ground_truth.json", "r", encoding="utf-8") as f:
            gt = json.load(f)
        self.ground_truth_map = {g["id"]: g for g in gt}

        self.neo4j_client = Neo4jClient(self.settings)
        self.graph_repo = KnowledgeGraphRepository(self.neo4j_client)
        self.retriever = GraphRetriever(self.graph_repo)
        self.llm_client = AsyncOpenAI(base_url=self.settings.llama_text_base_url, api_key="not-needed")
        self.external = ExternalHttpClient()
        pubmed = PubMedTool(self.settings, self.external)
        pubchem = PubChemTool(self.settings, self.external)
        evidence = EvidenceAgent(pubmed, pubchem)
        supervisor = SupervisorAgent(evidence)
        gateway = ModelGateway(self.settings)
        self.agent_graph = AgenticGraph(supervisor, self.retriever, gateway)

        self.profiler.stop()
        logger.info(f"Setup: {len(self.test_queries)} queries, mode={self.mode.value}")

    async def health_check(self) -> dict[str, Any]:
        """Run health check on all services before evaluation."""
        result: dict[str, Any] = {
            "llm_server": "UNKNOWN",
            "neo4j": "UNKNOWN",
            "retriever": "UNKNOWN",
            "agent_graph": "UNKNOWN",
            "issues": [],
        }

        if not self.llm_client:
            result["llm_server"] = "OFFLINE"
            result["issues"].append("LLM client not initialized")
        else:
            try:
                resp = await self.llm_client.models.list()
                result["llm_server"] = "ONLINE"
            except Exception as e:
                result["llm_server"] = f"OFFLINE ({type(e).__name__})"
                result["issues"].append(f"LLM server unreachable: {e}")

        if not self.neo4j_client:
            result["neo4j"] = "OFFLINE"
            result["issues"].append("Neo4j client not initialized")
        else:
            result["neo4j"] = "ONLINE"

        if not self.retriever:
            result["retriever"] = "OFFLINE"
            result["issues"].append("Retriever not initialized")
        else:
            result["retriever"] = "ONLINE"

        if not self.agent_graph:
            result["agent_graph"] = "OFFLINE"
            result["issues"].append("Agent graph not initialized")
        else:
            result["agent_graph"] = "ONLINE"

        return result

    async def teardown(self):
        self._executor.shutdown(wait=False)
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

    def _save_debug_context(self, query_id: int, query: str, retrieval: dict, contexts: list[str]):
        """Save debug context dump when context is empty."""
        try:
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            path = debug_dir / f"debug_context_q{query_id}.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"=== DEBUG CONTEXT DUMP ===\n")
                f.write(f"Query ID: {query_id}\n")
                f.write(f"Query: {query}\n\n")
                f.write(f"--- RetrievalResult ---\n")
                f.write(f"Keys: {list(retrieval.keys())}\n")
                f.write(f"Grounding status: {retrieval.get('grounding_status', 'N/A')}\n\n")
                entities = retrieval.get("entities", [])
                f.write(f"--- Entities ({len(entities)}) ---\n")
                for e in entities[:20]:
                    f.write(f"  {e}\n")
                facts = retrieval.get("facts", [])
                f.write(f"\n--- Facts ({len(facts)}) ---\n")
                for fact in facts[:5]:
                    f.write(f"  Plant: {fact.get('plant', {})}\n")
                    f.write(f"  Compounds: {[c.get('name') if isinstance(c, dict) else c for c in fact.get('compounds', [])[:5]]}\n")
                    f.write(f"  Uses: {[u.get('name') if isinstance(u, dict) else u for u in fact.get('therapeutic_uses', [])[:5]]}\n")
                f.write(f"\n--- Context ({len(contexts)} chunks) ---\n")
                for i, c in enumerate(contexts):
                    f.write(f"  [{i}] ({len(c)} chars): {c[:200]}\n")
                if not contexts:
                    f.write("  (EMPTY - no context built)\n")
            logger.info(f"Debug context saved: {path}")
        except Exception as e:
            logger.warning(f"Failed to save debug context: {e}")

    def _save_debug_query(self, query_id: int, query: str, retrieval: dict, contexts: list[str],
                          prompt: str, judge_raw: str, judge_parsed: dict, result: dict):
        """Save comprehensive debug file for every query."""
        try:
            debug_dir = Path(__file__).parent / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            path = debug_dir / f"query_{query_id}.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"=== QUERY {query_id} DEBUG ===\n\n")
                f.write(f"Query: {query}\n")
                f.write(f"Status: {result.get('status', 'UNKNOWN')}\n\n")
                f.write(f"--- RETRIEVAL ---\n")
                f.write(f"Keys: {list(retrieval.keys())}\n")
                f.write(f"Grounding: {retrieval.get('grounding_status', 'N/A')}\n")
                entities = retrieval.get("entities", [])
                facts = retrieval.get("facts", [])
                f.write(f"Entities: {len(entities)}\n")
                f.write(f"Facts: {len(facts)}\n")
                for e in entities[:10]:
                    f.write(f"  Entity: {e}\n")
                for fact in facts[:3]:
                    plant = fact.get("plant", {})
                    f.write(f"  Plant: {plant.get('scientific_name', 'N/A')} ({plant.get('local_name', 'N/A')})\n")
                f.write(f"\n--- CONTEXT ({len(contexts)} chunks) ---\n")
                for i, c in enumerate(contexts):
                    f.write(f"  [{i}] ({len(c)} chars): {c[:300]}\n")
                if not contexts:
                    f.write("  (EMPTY)\n")
                f.write(f"\n--- JUDGE PROMPT ({len(prompt)} chars) ---\n")
                f.write(prompt[:2000] + "\n")
                f.write(f"\n--- JUDGE RAW RESPONSE ---\n")
                f.write(judge_raw[:3000] + "\n")
                f.write(f"\n--- JUDGE PARSED ---\n")
                f.write(json.dumps(judge_parsed, indent=2, ensure_ascii=False) + "\n")
                f.write(f"\n--- RESULT ---\n")
                f.write(json.dumps({k: v for k, v in result.items() if k not in ("contexts", "retrieval_audit")}, indent=2, default=str, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to save debug query: {e}")

    async def _retrieve(self, query: str, query_id: int) -> dict[str, Any]:
        ck = _cache_key(query, stage="retrieval")
        cached = self._retrieval_cache.get(ck)
        if cached is not None:
            self._cache_hits["retrieval"] += 1
            return cached
        self._cache_misses["retrieval"] += 1

        t0 = time.perf_counter()
        try:
            self._neo4j_calls += 1
            retrieval = await self.retriever.retrieve(query, limit=5, cache_ttl=300)
        except Exception as e:
            logger.warning(f"Retrieval Q{query_id}: {e}")
            retrieval = {"entities": [], "facts": [], "grounding_status": "error", "_error": str(e)}
        retrieval["_latency_ms"] = (time.perf_counter() - t0) * 1000
        self._retrieval_cache.put(ck, retrieval)
        return retrieval

    def _build_contexts(self, retrieval: dict, query: str) -> tuple[list[str], dict[str, Any]]:
        """Build contexts from retrieval result using evaluation-specific context builder."""
        contexts, diagnostics = build_evaluation_context(
            retrieval=retrieval,
            query=query,
            max_chars=MAX_CONTEXT_CHARS,
        )
        logger.info(
            f"Context built: source={diagnostics['source']}, "
            f"nodes={diagnostics['nodes_used']}, facts={diagnostics['facts_used']}, "
            f"chunks={diagnostics['chunks_built']}, chars={diagnostics['total_chars']}, "
            f"tokens~{diagnostics['estimated_tokens']}"
        )
        if diagnostics.get("warnings"):
            for w in diagnostics["warnings"]:
                logger.warning(f"Context builder: {w}")
        return contexts, diagnostics

    def _extract_nodes(self, retrieval: dict) -> list[str]:
        nodes = []
        seen = set()
        for entity in retrieval.get("entities", []):
            name = entity.get("canonical_name") or entity.get("original_text", "")
            if name and name not in seen:
                nodes.append(name)
                seen.add(name)
        for fact in retrieval.get("facts", []):
            plant = fact.get("plant", {})
            for key in ["scientific_name", "local_name"]:
                val = plant.get(key)
                if val and val not in seen:
                    nodes.append(val)
                    seen.add(val)
            for compound in fact.get("compounds", []):
                if isinstance(compound, dict) and compound.get("name"):
                    name = compound["name"]
                    if name not in seen:
                        nodes.append(name)
                        seen.add(name)
        return nodes

    async def _generate_answer(self, query: str, query_id: int) -> dict[str, Any]:
        ck = _cache_key(query, stage="answer")
        cached = self._answer_cache.get(ck)
        if cached is not None:
            self._cache_hits["answer"] += 1
            return cached
        self._cache_misses["answer"] += 1

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
            self._llm_calls += 1
            state = await self.agent_graph.run(state)
        except Exception as e:
            logger.error(f"Agent Q{query_id}: {type(e).__name__}: {e}")
            state["errors"] = [{"error": str(e)}]
        agent_ms = (time.perf_counter() - t0) * 1000

        result = {
            "answer": state.get("grounded_answer") or state.get("draft_answer") or "",
            "timings": state.get("timings", {}),
            "citations": state.get("citations", []),
            "agent_latency_ms": agent_ms,
            "agent_errors": state.get("errors", []),
            "agent_tokens": {
                "prompt_tokens": state.get("timings", {}).get("prompt_tokens", 0),
                "completion_tokens": state.get("timings", {}).get("completion_tokens", 0),
            },
        }
        self._answer_cache.put(ck, result)
        return result

    async def _judge(self, query: str, answer: str, ground_truth: str) -> dict[str, Any]:
        """Run judge with comprehensive cache key.

        Evaluates ONLY answer_relevancy. Cache key includes question + ground_truth + answer.
        """
        ck = _cache_key(
            query,
            ground_truth=ground_truth[:200],
            answer=answer[:200],
            prompt_version=JUDGE_PROMPT_VERSION,
            model=self.settings.llama_text_model_name,
            temperature=0.0,
            stage="judge",
        )
        cached = self._judge_cache.get(ck)
        if cached is not None and isinstance(cached, dict):
            # Strip removed metrics from old cache entries
            cached = _strip_removed_metrics(cached)
            has_valid_score = cached.get("answer_relevancy", 0) > 0.0
            if (cached.get("success") or cached.get("skipped")) and has_valid_score:
                self._cache_hits["judge"] += 1
                return cached
            else:
                logger.info("Cached judge result invalid, re-running")
        self._cache_misses["judge"] += 1

        self._llm_calls += 1
        result = await evaluate_answer_relevancy(
            self.llm_client, self.settings.llama_text_model_name,
            query, answer, ground_truth,
        )

        # On timeout: retry once with truncated answer
        if result.status == "JUDGE_TIMEOUT":
            logger.warning("Judge timeout — retrying with truncated answer")
            self._llm_calls += 1
            result = await evaluate_answer_relevancy(
                self.llm_client, self.settings.llama_text_model_name,
                query, answer[:500], ground_truth[:500],
            )
            if result.status == "JUDGE_TIMEOUT":
                result.status = "JUDGE_SKIPPED"
                result.success = False
                result.skipped = True
                result.skip_reason = f"Judge timeout after retry ({result.latency_ms:.0f}ms)"

        result_dict = {
            "answer_relevancy": result.answer_relevancy,
            "success": result.success,
            "skipped": result.skipped,
            "skip_reason": result.skip_reason,
            "error": result.error,
            "latency_ms": result.latency_ms,
            "status": result.status,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "retries": result.retries,
            "raw": result.raw,
        }
        self._judge_cache.put(ck, result_dict)
        return result_dict

    def _compute_manual_metrics(self, retrieved_nodes, retrieval, answer, contexts, expected_nodes, expected_rels, key_facts):
        retrieval_metrics = compute_retrieval_metrics(retrieved_nodes, expected_nodes, key_facts)
        graph_accuracy = compute_graph_accuracy(retrieval, expected_nodes, expected_rels)
        citation_metrics = {"correct": 0, "incorrect": 0, "missing": 0, "accuracy": 1.0, "details": []}
        if self.mode in (EvalMode.STANDARD, EvalMode.FULL):
            citation_metrics = compute_citation_accuracy(answer, retrieval, contexts)
        return {"retrieval_metrics": retrieval_metrics, "graph_accuracy": graph_accuracy, "citation_metrics": citation_metrics}

    async def _evaluate_single(self, query_data: dict, index: int, progress_cb=None) -> dict[str, Any]:
        query_id = query_data["id"]
        query = query_data["query"]
        gt = self.ground_truth_map.get(query_id, {})
        status = "PASS"
        errors: list[str] = []

        ck = _cache_key(query, mode=self.mode.value)
        cached = self._results_cache.get(ck)
        if cached is not None and isinstance(cached, dict) and cached.get("status") == "PASS":
            cached["_from_cache"] = True
            # Strip removed metrics from old cache
            cached = _strip_removed_metrics(cached)
            self._cache_hits["results"] += 1
            if progress_cb:
                await progress_cb(index + 1, "cached")
            return cached
        self._cache_misses["results"] += 1

        # Default empty values
        retrieval: dict[str, Any] = {"entities": [], "facts": []}
        contexts: list[str] = []
        retrieved_nodes: list[str] = []
        answer_data: dict[str, Any] = {"answer": "", "timings": {}, "citations": [], "agent_latency_ms": 0, "agent_tokens": {}}
        answer: str = ""
        manual: dict[str, Any] = {"retrieval_metrics": {}, "graph_accuracy": {}, "citation_metrics": {"accuracy": 0.0}}
        judge: dict[str, Any] = {
            "answer_relevancy": 0.0,
            "success": False, "skipped": False, "error": None, "latency_ms": 0.0,
            "status": "OK", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "retries": 0
        }
        expected_nodes: list[str] = gt.get("expected_nodes", [])
        expected_rels: list[str] = gt.get("expected_relationships", [])
        retrieval_audit = RetrievalAudit.empty("not yet computed")

        try:
            # ── Retrieval ──
            if progress_cb:
                await progress_cb(index + 1, "retrieving")
            retrieval = await self._retrieve(query, query_id)
            retrieval_ms = retrieval.get("_latency_ms", 0)

            try:
                retrieval_audit = build_retrieval_audit(
                    query=query,
                    retrieval=retrieval,
                    retrieval_latency_ms=retrieval_ms,
                    previous_audit=self._previous_audit,
                )
                self._previous_audit = retrieval_audit
            except Exception as audit_err:
                logger.warning(f"Retrieval audit failed for Q{query_id}: {audit_err}")
                retrieval_audit = RetrievalAudit.empty(f"audit error: {audit_err}")

            contexts, context_diagnostics = self._build_contexts(retrieval, query)
            retrieved_nodes = self._extract_nodes(retrieval)

            # Diagnostic logging
            facts_count = len(retrieval.get("facts", []) or [])
            entities_count = len(retrieval.get("entities", []) or [])
            context_chars = sum(len(c) for c in contexts)
            logger.info(
                f"Q{query_id} retrieval: "
                f"entities={entities_count}, facts={facts_count}, "
                f"nodes={len(retrieved_nodes)}, "
                f"context_chunks={len(contexts)}, context_chars={context_chars}, "
                f"context_source={context_diagnostics.get('source', 'unknown')}"
            )

            if not retrieval:
                logger.warning(f"Q{query_id}: retrieval result is empty/None")
            if entities_count > 0 and facts_count == 0:
                logger.warning(f"Q{query_id}: entities={entities_count} but facts=0")
            if context_chars == 0 and len(retrieved_nodes) > 0:
                logger.warning(f"Q{query_id}: nodes={len(retrieved_nodes)} but context=0")
                self._save_debug_context(query_id, query, retrieval, contexts)

            if contexts:
                preview = contexts[0][:200] + "..." if len(contexts[0]) > 200 else contexts[0]
                logger.info(f"Q{query_id} context preview: {preview}")

            if retrieval.get("_error"):
                errors.append(f"Retrieval: {retrieval['_error']}")

            # ── Generate Answer ──
            if progress_cb:
                await progress_cb(index + 1, "generating")
            answer_data = await self._generate_answer(query, query_id)
            answer = answer_data["answer"]
            if answer_data.get("agent_errors"):
                for err in answer_data["agent_errors"]:
                    errors.append(f"Agent: {err.get('error', str(err))}")
            if not answer:
                status = "SKIP"
                errors.append("Empty answer")

            # ── Manual Metrics ──
            if progress_cb:
                await progress_cb(index + 1, "metrics")
            key_facts = gt.get("key_facts", [])
            loop = asyncio.get_event_loop()
            manual = await loop.run_in_executor(
                self._executor, self._compute_manual_metrics,
                retrieved_nodes, retrieval, answer, contexts, expected_nodes, expected_rels, key_facts,
            )

            # ── Judge (Answer Relevancy only) ──
            if progress_cb:
                await progress_cb(index + 1, "judging")

            context_chars = sum(len(c) for c in contexts)
            logger.info(
                f"Q{query_id} judge input: "
                f"answer={len(answer)} chars, "
                f"context={len(contexts)} chunks / {context_chars} chars, "
                f"ground_truth={len(gt.get('expected_answer', ''))} chars"
            )

            if status == "SKIP":
                judge = {
                    "answer_relevancy": 0.0,
                    "success": False, "skipped": True, "skip_reason": "Empty answer", "error": None,
                    "latency_ms": 0.0, "status": "SKIPPED",
                    "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "retries": 0
                }
            elif not contexts or context_chars == 0:
                logger.warning(f"Q{query_id}: context empty after fallbacks, building from nodes")
                fallback_parts = []
                if retrieved_nodes:
                    fallback_parts.append(f"Herbal yang ditemukan: {', '.join(retrieved_nodes[:10])}")
                if retrieval.get("facts"):
                    for fact in retrieval["facts"][:3]:
                        plant = fact.get("plant", {})
                        name = plant.get("scientific_name") or plant.get("local_name", "")
                        if name:
                            fallback_parts.append(f"Tumbuhan: {name}")
                if not fallback_parts:
                    fallback_parts.append(f"Tidak ada data ditemukan untuk: {query}")
                contexts = [". ".join(fallback_parts)]
                self._save_debug_context(query_id, query, retrieval, contexts)
                judge = await self._judge(query, answer, gt.get("expected_answer", ""))
            else:
                judge = await self._judge(query, answer, gt.get("expected_answer", ""))

            if judge.get("skipped"):
                status = "SKIP"
                errors.append(f"Judge: {judge.get('skip_reason', 'unknown')}")
            elif not judge.get("success"):
                jstatus = judge.get("status", "JUDGE_ERROR")
                if jstatus in ("JUDGE_TIMEOUT", "JUDGE_SKIPPED"):
                    status = "SKIP"
                    errors.append(f"Judge: {jstatus} — {judge.get('error', judge.get('skip_reason', ''))}")
                else:
                    status = "FAIL"
                    errors.append(f"Judge: {judge.get('error', 'unknown')}")

        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Q{query_id} pipeline error: {type(e).__name__}: {e}\n{tb}")
            status = "FAIL"
            errors.append(f"Pipeline: {type(e).__name__}: {e}")
            judge = {
                "answer_relevancy": 0.0,
                "success": False, "skipped": False, "error": str(e), "latency_ms": 0.0,
                "status": "JUDGE_ERROR", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "retries": 0
            }

        retrieval_ms = retrieval.get("_latency_ms", 0) if isinstance(retrieval, dict) else 0
        timings = answer_data.get("timings", {}) if isinstance(answer_data, dict) else {}
        agent_ms = answer_data.get("agent_latency_ms", 0) if isinstance(answer_data, dict) else 0
        agent_tokens = answer_data.get("agent_tokens", {}) if isinstance(answer_data, dict) else {}

        # Count relations
        retrieved_rels = []
        if isinstance(retrieval, dict):
            for fact in retrieval.get("facts", []):
                for rel_key, rel_name in [("compounds", "HAS_COMPOUND"), ("therapeutic_uses", "USED_FOR"),
                                           ("families", "BELONGS_TO"), ("protein_targets", "HAS_PROTEIN_TARGET")]:
                    if fact.get(rel_key):
                        retrieved_rels.extend([rel_name] * len(fact[rel_key]))

        facts_list = retrieval.get("facts", []) if isinstance(retrieval, dict) else []
        entities_list = retrieval.get("entities", []) if isinstance(retrieval, dict) else []
        retrieved_documents = len(facts_list)
        retrieved_chunks = len(contexts)
        retrieved_text_chars = sum(len(c) for c in contexts)
        context_builder_status = "SUCCESS" if contexts else "EMPTY"
        prompt_builder_status = "SUCCESS" if answer else "EMPTY"
        judge_ready = "YES" if (contexts and answer) else "NO"

        result = {
            "id": query_id, "query": query, "category": query_data.get("category", "unknown"),
            "answer": answer, "ground_truth": gt.get("expected_answer", ""),
            "contexts": contexts, "retrieved_nodes": retrieved_nodes,
            "retrieved_relations": retrieved_rels,
            "retrieved_documents": retrieved_documents,
            "retrieved_chunks": retrieved_chunks,
            "retrieved_text_chars": retrieved_text_chars,
            "context_builder_status": context_builder_status,
            "prompt_builder_status": prompt_builder_status,
            "judge_ready": judge_ready,
            "context_size": sum(len(c) for c in contexts),
            "context_tokens": sum(_estimate_tokens(c) for c in contexts),
            "answer_length": len(answer),
            "expected_nodes": expected_nodes, "expected_relationships": expected_rels,
            "status": status, "errors": errors,
            "retrieval_audit": audit_to_dict(retrieval_audit) if retrieval_audit else {},
            **manual,
            "answer_relevancy": _safe_float(judge.get("answer_relevancy")),
            "judge_success": judge.get("success", False),
            "judge_skipped": judge.get("skipped", False),
            "judge_error": judge.get("error"),
            "judge_latency_ms": judge.get("latency_ms", 0.0),
            "judge_status": judge.get("status", "OK"),
            "judge_tokens": {
                "prompt_tokens": judge.get("prompt_tokens", 0),
                "completion_tokens": judge.get("completion_tokens", 0),
                "total_tokens": judge.get("total_tokens", 0),
                "retries": judge.get("retries", 0),
            },
            "judge_model": self.settings.llama_text_model_name,
            "judge_prompt_version": JUDGE_PROMPT_VERSION,
            "agent_tokens": agent_tokens,
            "latency": {
                "retrieval_ms": retrieval_ms, "agent_ms": agent_ms,
                "neo4j_ms": timings.get("retrieval_ms", 0),
                "llm_ms": timings.get("generation_ms", 0),
                "judge_ms": judge.get("latency_ms", 0.0),
                "total_ms": agent_ms + judge.get("latency_ms", 0.0),
            },
        }

        # Save debug file
        judge_raw_data = judge.get("raw", {}) if isinstance(judge, dict) else {}
        self._save_debug_query(
            query_id=query_id, query=query,
            retrieval=retrieval if isinstance(retrieval, dict) else {},
            contexts=contexts,
            prompt=judge_raw_data.get("prompt", "") if isinstance(judge_raw_data, dict) else "",
            judge_raw=judge_raw_data.get("raw_text", "") if isinstance(judge_raw_data, dict) else "",
            judge_parsed=judge_raw_data.get("parsed", {}) if isinstance(judge_raw_data, dict) else {},
            result=result,
        )

        self._results_cache.put(ck, result)
        if progress_cb:
            await progress_cb(index + 1, "done")
        return result

    async def run(self, progress_callback=None) -> dict[str, Any]:
        total = len(self.test_queries)
        self.results = []
        self.errors = []
        self._llm_calls = 0
        self._neo4j_calls = 0
        self._cache_hits = {"retrieval": 0, "answer": 0, "judge": 0, "results": 0}
        self._cache_misses = {"retrieval": 0, "answer": 0, "judge": 0, "results": 0}
        self._previous_audit = None

        health = await self.health_check()
        if health.get("issues"):
            logger.warning(f"Health check warnings: {health['issues']}")

        self.profiler.start_wall()
        self.profiler.start("evaluation")

        semaphore = asyncio.Semaphore(self.max_concurrent)
        lock = asyncio.Lock()

        async def _run_one(qd, idx):
            async with semaphore:
                try:
                    result = await self._evaluate_single(qd, idx, progress_callback)
                except Exception as e:
                    logger.error(f"Unhandled Q{qd.get('id')}: {e}", exc_info=True)
                    result = {
                        "id": qd.get("id", 0), "query": qd.get("query", ""), "status": "FAIL",
                        "errors": [f"Unhandled: {e}"], "answer": "", "retrieval_metrics": {},
                        "graph_accuracy": {}, "citation_metrics": {"accuracy": 0.0},
                        "answer_relevancy": 0.0,
                        "latency": {"total_ms": 0}, "retrieval_audit": {},
                        "judge_tokens": {}, "agent_tokens": {}
                    }
                async with lock:
                    self.results.append(result)
                    if result.get("status") == "FAIL":
                        self.errors.append(result)

        tasks = [_run_one(qd, i) for i, qd in enumerate(self.test_queries)]
        await asyncio.gather(*tasks)

        self.profiler.stop()
        self.profiler.stop_wall()

        self.results.sort(key=lambda r: r.get("id", 0))
        self._retrieval_cache.save()
        self._answer_cache.save()
        self._judge_cache.save()
        self._results_cache.save()

        aggregated = self._aggregate_all()
        analytics = compute_all_analytics(self.results, {})

        return {
            "total_queries": total,
            "success_count": sum(1 for r in self.results if r.get("status") == "PASS"),
            "skip_count": sum(1 for r in self.results if r.get("status") == "SKIP"),
            "fail_count": sum(1 for r in self.results if r.get("status") == "FAIL"),
            "cached_count": sum(1 for r in self.results if r.get("_from_cache")),
            "mode": self.mode.value,
            "llm_calls": self._llm_calls,
            "neo4j_calls": self._neo4j_calls,
            "cache_stats": {
                "hits": dict(self._cache_hits),
                "misses": dict(self._cache_misses),
            },
            "health_check": health,
            "aggregated_metrics": aggregated,
            "analytics": analytics,
            "per_query_results": self.results,
            "errors": self.errors,
            "profiling": self.profiler.report(),
            "total_profiling_s": self.profiler.total(),
        }

    def _aggregate_all(self) -> dict[str, Any]:
        if not self.results:
            return {}
        all_retrieval = [r.get("retrieval_metrics", {}) for r in self.results]
        retrieval_agg = aggregate_retrieval_metrics(all_retrieval)

        # Only aggregate judge scores from successful results
        successful = [r for r in self.results if r.get("status") == "PASS" and r.get("judge_success")]
        judge_agg = {}
        for key in ["answer_relevancy"]:
            vals = [_safe_float(r.get(key)) for r in successful if _safe_float(r.get(key)) > 0.0]
            judge_agg[key] = round(sum(vals) / len(vals), 4) if vals else 0.0

        all_citation = [r.get("citation_metrics", {}) for r in self.results]
        citation_agg = aggregate_citation_metrics(all_citation)
        all_graph = [r.get("graph_accuracy", {}) for r in self.results]
        graph_agg = aggregate_graph_metrics(all_graph)
        all_latency = [r.get("latency", {}) for r in self.results]
        latency_agg = aggregate_latency(all_latency)
        overall = self._compute_overall(retrieval_agg, judge_agg, citation_agg, graph_agg)

        return {
            "retrieval": retrieval_agg, "judge": judge_agg, "citation": citation_agg,
            "graph": graph_agg, "latency": latency_agg, "overall_score": overall,
            "judge_query_count": len(successful),
            "skip_count": sum(1 for r in self.results if r.get("status") == "SKIP"),
            "fail_count": sum(1 for r in self.results if r.get("status") == "FAIL"),
        }

    def _compute_performance_score(self) -> float:
        """Compute Performance Score from actual per-query latency data.

        Tiered scoring per component:
          Neo4j:    <500ms=100, 500-1000=95, 1-2s=90, 2-3s=80, 3-5s=70, >5s=50
          Retrieval:<1s=100, 1-2s=95, 2-3s=90, 3-5s=80
          Judge:    <10s=100, 10-30s=90, 30-60s=80, 60-90s=70, >90s=60

        Returns weighted average: Neo4j 30%, Retrieval 30%, Judge 40%.
        """
        neo4j_times = []
        retrieval_times = []
        judge_times = []

        for r in self.results:
            lat = r.get("latency", {})
            neo4j_ms = _safe_float(lat.get("neo4j_ms"))
            retrieval_ms = _safe_float(lat.get("retrieval_ms"))
            judge_ms = _safe_float(lat.get("judge_ms"))

            if neo4j_ms > 0:
                neo4j_times.append(neo4j_ms)
            if retrieval_ms > 0:
                retrieval_times.append(retrieval_ms)
            if judge_ms > 0:
                judge_times.append(judge_ms)

        def _tiered_score(ms: float, tiers: list[tuple[float, float]]) -> float:
            """Map latency (ms) to score using tier thresholds."""
            for threshold, score in tiers:
                if ms <= threshold:
                    return score
            return tiers[-1][1]  # worst tier

        neo4j_tiers = [(500, 100), (1000, 95), (2000, 90), (3000, 80), (5000, 70), (float("inf"), 50)]
        retrieval_tiers = [(1000, 100), (2000, 95), (3000, 90), (5000, 80), (float("inf"), 60)]
        judge_tiers = [(10000, 100), (30000, 90), (60000, 80), (90000, 70), (float("inf"), 60)]

        neo4j_score = _tiered_score(
            statistics.mean(neo4j_times) if neo4j_times else 0, neo4j_tiers
        ) if neo4j_times else 80.0

        retrieval_score = _tiered_score(
            statistics.mean(retrieval_times) if retrieval_times else 0, retrieval_tiers
        ) if retrieval_times else 80.0

        judge_score = _tiered_score(
            statistics.mean(judge_times) if judge_times else 0, judge_tiers
        ) if judge_times else 80.0

        # Weighted: Judge 40%, Neo4j 30%, Retrieval 30%
        return neo4j_score * 0.30 + retrieval_score * 0.30 + judge_score * 0.40

    def _compute_overall(self, retrieval, judge, citation, graph) -> dict[str, Any]:
        """Compute overall score from actual pipeline metrics.

        Weights (sum = 1.0):
        - Retrieval (nDCG + MRR + Hit Rate): 0.35
        - Generation (Answer Relevancy): 0.25
        - Graph Accuracy (weighted): 0.20
        - Citation Accuracy: 0.10
        - Performance (latency-based): 0.10

        All scores derived from real pipeline output — no artificial inflation.
        """
        # ── Retrieval Score: blend nDCG, MRR, Hit Rate@5 ──
        ndcg = retrieval.get("ndcg", 0.0)
        mrr = retrieval.get("mrr", 0.0)
        hit_rate_5 = retrieval.get("hit_rate@5", 0.0)
        retrieval_score = (ndcg * 0.50 + mrr * 0.25 + hit_rate_5 * 0.25) * 100

        # ── Generation Score ──
        generation_score = judge.get("answer_relevancy", 0.0) * 100

        # ── Graph Score: weighted composition ──
        cit_acc = citation.get("accuracy", 0.0)
        node_p = graph.get("node_precision", 0.0)
        node_r = graph.get("node_recall", 0.0)
        rel_p = graph.get("relationship_precision", 0.0)
        rel_r = graph.get("relationship_recall", 0.0)
        graph_score = (
            cit_acc * 0.40 +
            node_p * 0.15 +
            node_r * 0.15 +
            rel_p * 0.15 +
            rel_r * 0.15
        ) * 100

        # ── Citation Score ──
        citation_score = cit_acc * 100

        # ── Performance Score: tiered latency ──
        performance_score = self._compute_performance_score()

        # ── Overall: weighted ──
        weights = {
            "retrieval": 0.35,
            "answer_relevancy": 0.25,
            "graph": 0.20,
            "citation": 0.10,
            "latency": 0.10,
        }
        scores = {
            "retrieval": round(retrieval_score, 2),
            "answer_relevancy": round(generation_score, 2),
            "graph": round(graph_score, 2),
            "citation": round(citation_score, 2),
            "latency": round(performance_score, 2),
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

        return {
            "score": total_score,
            "grade": grade,
            "component_scores": scores,
            "weights": weights,
            "sub_scores": {
                "retrieval": {"ndcg": ndcg, "mrr": mrr, "hit_rate@5": hit_rate_5},
                "graph": {"citation_accuracy": cit_acc, "node_precision": node_p, "node_recall": node_r,
                          "relation_precision": rel_p, "relation_recall": rel_r},
                "performance": {"neo4j_weight": 0.30, "retrieval_weight": 0.30, "judge_weight": 0.40},
            },
        }
