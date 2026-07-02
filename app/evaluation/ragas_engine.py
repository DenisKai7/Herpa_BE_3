"""Isolated Ragas evaluation engine for HERPA GraphRAG pipeline.

Zero disruption to production code — only imports existing functions.
"""

import logging
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from app.agents.evidence_agent import EvidenceAgent
from app.agents.graph import AgenticGraph
from app.agents.state import AgentState
from app.agents.supervisor import SupervisorAgent
from app.graph.context_builder import format_herb_fact
from app.graph.retriever import GraphRetriever
from app.services.ai.model_gateway import ModelGateway
from app.services.external.http_client import ExternalHttpClient
from app.services.external.pubchem import PubChemTool
from app.services.external.pubmed import PubMedTool

logger = logging.getLogger(__name__)


class EvaluationTestCase(BaseModel):
    """Single evaluation test case with question and expected ground truth."""

    question: str
    ground_truth: str


class EvaluationResult(BaseModel):
    """Aggregated evaluation result."""

    overall_metrics: dict[str, Any] = Field(default_factory=dict)
    per_test_case: list[dict[str, Any]] = Field(default_factory=list)
    test_case_count: int = 0
    elapsed_seconds: float = 0.0
    csv_path: str | None = None
    error: str | None = None


DEFAULT_TEST_CASES: list[EvaluationTestCase] = [
    EvaluationTestCase(
        question="Apa manfaat jeruk nipis untuk kesehatan?",
        ground_truth=(
            "Jeruk nipis (Citrus aurantifolia) memiliki manfaat kesehatan antara lain: "
            "kaya vitamin C yang berperan sebagai antioksidan, mendukung sistem imun, "
            "membantu pencernaan, dan memiliki sifat antimikroba. "
            "Senyawa aktifnya meliputi limonen, asam sitrat, dan flavonoid."
        ),
    ),
    EvaluationTestCase(
        question="Apa saja senyawa aktif yang terdapat pada bawang putih?",
        ground_truth=(
            "Bawang putih (Allium sativum) mengandung senyawa aktif utama yaitu allicin, "
            "ajone, dialil disulfida (DADS), dan S-allyl cysteine. "
            "Senyawa-senyawa ini termasuk dalam kelompok organosulfur dan memiliki aktivitas "
            "antimikroba, antiinflamasi, serta potensi kardiotonik."
        ),
    ),
    EvaluationTestCase(
        question="Apa kegunaan terapeutik ginseng?",
        ground_truth=(
            "Ginseng (Panax ginseng) memiliki kegunaan terapeutik meliputi: "
            "adaptogen untuk meningkatkan daya tahan tubuh, meningkatkan energi dan vitalitas, "
            "membantu fungsi kognitif, serta memiliki sifat antioksidan. "
            "Senyawa aktif utamanya adalah ginsenosida."
        ),
    ),
    EvaluationTestCase(
        question="Apa kandungan fitokimia temulawak?",
        ground_truth=(
            "Temulawak (Curcuma xanthorrhiza) mengandung fitokimia utama yaitu kurkumin, "
            "xanthorrhizol, dan germakron. Senyawa-senyawa ini memberikan aktivitas "
            "hepatoprotektif, antiinflamasi, dan antioksidan. "
            "Temulawak digunakan secara tradisional untuk menjaga kesehatan hati dan pencernaan."
        ),
    ),
]


def _build_eval_llm(settings: Any) -> Any:
    """Build LangChain ChatOpenAI instance pointing to the local Llama endpoint."""
    try:
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "not-needed")
        return ChatOpenAI(
            base_url=settings.llama_text_base_url,
            api_key=api_key,
            model=settings.llama_text_model_name,
            temperature=0.1,
            timeout=settings.text_model_timeout_seconds,
            max_tokens=512,
        )
    except ImportError:
        logger.warning("langchain-openai not installed; Ragas LLM wrapper unavailable")
        return None


async def _retrieve_contexts(
    retriever: GraphRetriever, question: str
) -> list[str]:
    """Retrieve knowledge graph facts and convert to list of context strings."""
    result = await retriever.retrieve(question, limit=5)
    contexts: list[str] = []
    for fact in result.get("facts", []):
        text = format_herb_fact(fact)
        if text.strip():
            contexts.append(text)
    return contexts


async def _generate_answer(
    agent_graph: AgenticGraph, question: str
) -> str:
    """Run the full agent pipeline and capture the generated answer."""
    state: AgentState = {
        "request_id": f"eval-{int(time.time())}",
        "user_id": "eval-system",
        "application_role": "user",
        "persona": "umum",
        "model_mode": "fast-medium",
        "requested_mode": "fast-medium",
        "execution_mode_used": "fast-medium",
        "chat_id": None,
        "user_query": question,
        "attachment_ids": [],
        "attachment_context": [],
        "errors": [],
        "timings": {
            "auth_ms": 0,
            "profile_ms": 0,
            "retrieval_ms": 0,
            "ttft_ms": 0,
            "generation_ms": 0,
            "persistence_ms": 0,
            "total_ms": 0,
        },
    }
    state = await agent_graph.run(state)
    return state.get("grounded_answer") or state.get("draft_answer") or ""


async def run_evaluation(
    services: Any,
    test_cases: list[EvaluationTestCase] | None = None,
) -> EvaluationResult:
    """Execute the full Ragas evaluation pipeline.

    Args:
        services: The app's Services dataclass (from app.state.services).
        test_cases: Optional list of test cases; defaults to DEFAULT_TEST_CASES.

    Returns:
        EvaluationResult with metrics and per-test-case breakdown.
    """
    started = time.perf_counter()
    cases = test_cases or DEFAULT_TEST_CASES
    result = EvaluationResult(test_case_count=len(cases))

    try:
        # Lazy-import Ragas dependencies to avoid import-time failures
        # when the library is not installed.
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        settings = services.settings
        retriever = GraphRetriever(services.graph_repository)
        external = ExternalHttpClient()
        pubmed = PubMedTool(settings, external)
        pubchem = PubChemTool(settings, external)
        evidence = EvidenceAgent(pubmed, pubchem)
        supervisor = SupervisorAgent(evidence)
        agent_graph = AgenticGraph(supervisor, retriever, services.model_gateway)

        questions: list[str] = []
        answers: list[str] = []
        contexts_list: list[list[str]] = []
        ground_truths: list[str] = []
        per_case: list[dict[str, Any]] = []

        for case in cases:
            logger.info("eval_processing", extra={"question": case.question})
            try:
                contexts = await _retrieve_contexts(retriever, case.question)
                answer = await _generate_answer(agent_graph, case.question)
            except Exception as exc:
                logger.warning("eval_case_failed", extra={"question": case.question, "error": str(exc)})
                contexts = []
                answer = f"[Error: {exc}]"

            questions.append(case.question)
            answers.append(answer)
            contexts_list.append(contexts if contexts else ["Tidak ada konteks ditemukan."])
            ground_truths.append(case.ground_truth)
            per_case.append({
                "question": case.question,
                "ground_truth": case.ground_truth,
                "answer": answer,
                "contexts": contexts,
            })

        # Build HuggingFace Dataset
        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths,
        })

        # Configure Ragas LLM — prefer local Llama endpoint, fallback to OpenAI
        eval_llm = _build_eval_llm(settings)
        ragas_kwargs: dict[str, Any] = {}
        if eval_llm is not None:
            try:
                from ragas.llms import LangchainLLMWrapper
                from ragas.embeddings import LangchainEmbeddingsWrapper
                from langchain_openai import OpenAIEmbeddings

                ragas_llm = LangchainLLMWrapper(eval_llm)
                ragas_kwargs["llm"] = ragas_llm

                # Build embeddings — use local endpoint or dummy
                try:
                    embed_model = OpenAIEmbeddings(
                        base_url=settings.llama_text_base_url,
                        api_key=os.environ.get("OPENAI_API_KEY", "not-needed"),
                    )
                    ragas_kwargs["embeddings"] = LangchainEmbeddingsWrapper(embed_model)
                except Exception:
                    logger.warning("Embeddings model unavailable; Ragas may use defaults")
            except ImportError:
                logger.warning("ragas llm wrapper import failed; using defaults")

        # Run Ragas evaluation
        eval_result = evaluate(
            dataset=dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            **ragas_kwargs,
        )

        # Extract scores
        overall = {}
        if hasattr(eval_result, "scores"):
            scores = eval_result.scores
            if isinstance(scores, dict):
                for metric_name, values in scores.items():
                    if isinstance(values, list) and values:
                        overall[metric_name] = sum(values) / len(values)
                    else:
                        overall[metric_name] = values
            elif isinstance(scores, list):
                for metric_name in ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]:
                    vals = [row.get(metric_name) for row in scores if row.get(metric_name) is not None]
                    if vals:
                        overall[metric_name] = sum(vals) / len(vals)

        # Attach per-case scores
        if hasattr(eval_result, "scores") and isinstance(eval_result.scores, list):
            for i, score_row in enumerate(eval_result.scores):
                if i < len(per_case):
                    per_case[i]["metrics"] = score_row

        result.overall_metrics = overall
        result.per_test_case = per_case

        # Export CSV
        csv_dir = os.path.join(os.getcwd(), "storage", "logs")
        os.makedirs(csv_dir, exist_ok=True)
        csv_path = os.path.join(csv_dir, "ragas_report.csv")
        try:
            df = eval_result.to_pandas()
            df.to_csv(csv_path, index=False)
            result.csv_path = csv_path
            logger.info("ragas_csv_saved", extra={"path": csv_path})
        except Exception as csv_exc:
            logger.warning("ragas_csv_save_failed", extra={"error": str(csv_exc)})

        # Close external HTTP client
        try:
            await external.close()
        except Exception:
            pass

    except ImportError as exc:
        logger.error("ragas_import_error", extra={"error": str(exc)})
        result.error = (
            f"Ragas dependencies not installed: {exc}. "
            "Install with: pip install ragas datasets langchain-openai"
        )
    except Exception as exc:
        logger.exception("ragas_evaluation_failed")
        result.error = f"Evaluation failed: {type(exc).__name__}: {exc}"

    result.elapsed_seconds = round(time.perf_counter() - started, 2)
    return result
