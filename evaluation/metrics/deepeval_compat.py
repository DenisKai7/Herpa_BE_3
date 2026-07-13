"""DeepEval-compatible RAG metrics using local LLM (OpenAI-compatible API).

Drop-in replacement when deepeval package is unavailable.
Same metric names, same score semantics (0-1), swappable when deepeval is installed.

Metrics implemented:
- AnswerRelevancyMetric
- FaithfulnessMetric
- ContextualPrecisionMetric
- ContextualRecallMetric
- ContextualRelevancyMetric
- HallucinationMetric
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# ─── Shared LLM caller ───────────────────────────────────────────────────────

async def _llm_json(
    client: AsyncOpenAI,
    model: str,
    prompt: str,
    max_tokens: int = 300,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Call LLM and parse JSON response. Single call, no retries."""
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content.strip()
        # Strip markdown fences
        if "```" in text:
            text = text.split("```")[1].strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting JSON object/array from text
        match = re.search(r'[\[{].*[\]}]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {}
    except Exception as e:
        logger.debug(f"LLM call failed: {e}")
        return {}


# ─── Metric result ───────────────────────────────────────────────────────────

@dataclass
class MetricResult:
    name: str
    score: float  # 0-1
    reason: str = ""
    success: bool = True
    error: str | None = None


# ─── Answer Relevancy ────────────────────────────────────────────────────────

_ANSWER_RELEVANCY_PROMPT = """You are an evaluation judge. Rate how relevant the answer is to the question.

Question: {question}

Answer: {answer}

Respond with JSON only: {{"score": <0.0-1.0>, "reason": "<brief reason>"}}"""


async def answer_relevancy(
    client: AsyncOpenAI,
    model: str,
    question: str,
    answer: str,
) -> MetricResult:
    if not answer:
        return MetricResult("answer_relevancy", 0.0, "No answer", success=False)
    prompt = _ANSWER_RELEVANCY_PROMPT.format(question=question, answer=answer[:2000])
    data = await _llm_json(client, model, prompt)
    score = float(data.get("score", 0.0))
    return MetricResult("answer_relevancy", max(0.0, min(1.0, score)), data.get("reason", ""))


# ─── Faithfulness ────────────────────────────────────────────────────────────

_FAITHFULNESS_PROMPT = """You are an evaluation judge. Check if the answer is faithful to (supported by) the given context.

Context:
{context}

Answer: {answer}

For each claim in the answer, determine if it is supported by the context.
Respond with JSON: {{"score": <0.0-1.0>, "supported_claims": <int>, "total_claims": <int>, "reason": "<brief>"}}"""


async def faithfulness(
    client: AsyncOpenAI,
    model: str,
    answer: str,
    contexts: list[str],
) -> MetricResult:
    if not answer or not contexts:
        return MetricResult("faithfulness", 0.0, "Missing answer or context", success=False)
    ctx_text = "\n---\n".join(contexts[:5])[:3000]
    prompt = _FAITHFULNESS_PROMPT.format(context=ctx_text, answer=answer[:2000])
    data = await _llm_json(client, model, prompt)
    score = float(data.get("score", 0.0))
    return MetricResult("faithfulness", max(0.0, min(1.0, score)), data.get("reason", ""))


# ─── Contextual Precision ───────────────────────────────────────────────────

_CTX_PRECISION_PROMPT = """You are an evaluation judge. Rate how precise the retrieved contexts are relative to the question.

Question: {question}

Retrieved Contexts:
{contexts}

How many of the retrieved contexts are actually relevant to the question?
Respond with JSON: {{"score": <0.0-1.0>, "relevant_count": <int>, "total_count": <int>, "reason": "<brief>"}}"""


async def contextual_precision(
    client: AsyncOpenAI,
    model: str,
    question: str,
    contexts: list[str],
) -> MetricResult:
    if not contexts:
        return MetricResult("contextual_precision", 0.0, "No contexts", success=False)
    ctx_text = "\n---\n".join(contexts[:10])[:3000]
    prompt = _CTX_PRECISION_PROMPT.format(question=question, contexts=ctx_text)
    data = await _llm_json(client, model, prompt)
    score = float(data.get("score", 0.0))
    return MetricResult("contextual_precision", max(0.0, min(1.0, score)), data.get("reason", ""))


# ─── Contextual Recall ──────────────────────────────────────────────────────

_CTX_RECALL_PROMPT = """You are an evaluation judge. Rate how well the retrieved contexts cover the information needed to answer the question.

Question: {question}

Ground Truth Answer: {ground_truth}

Retrieved Contexts:
{contexts}

What fraction of the ground truth information is present in the retrieved contexts?
Respond with JSON: {{"score": <0.0-1.0>, "reason": "<brief>"}}"""


async def contextual_recall(
    client: AsyncOpenAI,
    model: str,
    question: str,
    ground_truth: str,
    contexts: list[str],
) -> MetricResult:
    if not contexts or not ground_truth:
        return MetricResult("contextual_recall", 0.0, "Missing context or ground truth", success=False)
    ctx_text = "\n---\n".join(contexts[:5])[:3000]
    prompt = _CTX_RECALL_PROMPT.format(
        question=question, ground_truth=ground_truth[:1500], contexts=ctx_text
    )
    data = await _llm_json(client, model, prompt)
    score = float(data.get("score", 0.0))
    return MetricResult("contextual_recall", max(0.0, min(1.0, score)), data.get("reason", ""))


# ─── Contextual Relevancy ───────────────────────────────────────────────────

_CTX_RELEVANCY_PROMPT = """You are an evaluation judge. Rate how relevant the retrieved contexts are to the question.

Question: {question}

Contexts:
{contexts}

Respond with JSON: {{"score": <0.0-1.0>, "reason": "<brief>"}}"""


async def contextual_relevancy(
    client: AsyncOpenAI,
    model: str,
    question: str,
    contexts: list[str],
) -> MetricResult:
    if not contexts:
        return MetricResult("contextual_relevancy", 0.0, "No contexts", success=False)
    ctx_text = "\n---\n".join(contexts[:5])[:3000]
    prompt = _CTX_RELEVANCY_PROMPT.format(question=question, contexts=ctx_text)
    data = await _llm_json(client, model, prompt)
    score = float(data.get("score", 0.0))
    return MetricResult("contextual_relevancy", max(0.0, min(1.0, score)), data.get("reason", ""))


# ─── Hallucination ──────────────────────────────────────────────────────────

_HALLUCINATION_PROMPT = """You are an evaluation judge. Detect hallucinations in the answer.

Context (grounded evidence):
{context}

Answer: {answer}

Count sentences in the answer that are NOT supported by the context.
Respond with JSON: {{"hallucinated_sentences": <int>, "total_sentences": <int>, "hallucination_rate": <0.0-1.0>, "reason": "<brief>"}}"""


async def hallucination_metric(
    client: AsyncOpenAI,
    model: str,
    answer: str,
    contexts: list[str],
) -> MetricResult:
    if not answer:
        return MetricResult("hallucination", 0.0, "No answer", success=False)
    ctx_text = "\n---\n".join(contexts[:5])[:3000]
    prompt = _HALLUCINATION_PROMPT.format(context=ctx_text, answer=answer[:2000])
    data = await _llm_json(client, model, prompt)
    rate = float(data.get("hallucination_rate", 0.0))
    # Return as "score" where 1.0 = no hallucination (best), 0.0 = all hallucinated
    score = 1.0 - max(0.0, min(1.0, rate))
    return MetricResult("hallucination", score, data.get("reason", ""))


# ─── Batch evaluator ─────────────────────────────────────────────────────────

async def evaluate_all_deepeval_metrics(
    client: AsyncOpenAI,
    model: str,
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
) -> dict[str, MetricResult]:
    """Run ALL DeepEval metrics in PARALLEL for a single query.

    This is the key optimization: all 6 LLM judge calls fire concurrently.
    """
    tasks = [
        answer_relevancy(client, model, question, answer),
        faithfulness(client, model, answer, contexts),
        contextual_precision(client, model, question, contexts),
        contextual_recall(client, model, question, ground_truth, contexts),
        contextual_relevancy(client, model, question, contexts),
        hallucination_metric(client, model, answer, contexts),
    ]

    # Use return_exceptions so one failure doesn't kill all
    results = await asyncio.gather(*tasks, return_exceptions=True)

    names = [
        "answer_relevancy",
        "faithfulness",
        "contextual_precision",
        "contextual_recall",
        "contextual_relevancy",
        "hallucination",
    ]

    output: dict[str, MetricResult] = {}
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            output[name] = MetricResult(name, 0.0, str(result), success=False, error=str(result))
        else:
            output[name] = result

    return output
