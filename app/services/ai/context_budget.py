from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.core.exceptions import AppError


@dataclass
class ContextBudget:
    context_size: int
    output_tokens: int
    safety_margin: int
    input_budget: int


def get_context_budget(context_size: int, output_tokens: int, safety_margin: int) -> ContextBudget:
    input_budget = context_size - output_tokens - safety_margin
    return ContextBudget(
        context_size=context_size,
        output_tokens=output_tokens,
        safety_margin=safety_margin,
        input_budget=input_budget,
    )


def estimate_tokens(text: str) -> int:
    # Conservative estimator: ~3 characters per token
    return max(1, len(text) // 3)


def fit_messages_to_context(
    messages: list[dict[str, Any]],
    context_size: int,
    max_output_tokens: int,
    safety_margin: int,
    persona: str = "umum",
    user_query: str = "",
) -> list[dict[str, Any]]:
    budget = get_context_budget(context_size, max_output_tokens, safety_margin)
    if budget.input_budget <= 0:
        raise AppError("MODEL_CONTEXT_OVERFLOW", "Kapasitas konteks model tidak cukup.", 413)

    fitted = deepcopy(messages)
    if _count(fitted) <= budget.input_budget:
        return fitted

    # We need to trim context fields (facts, attachments, history, evidence)
    # Since we construct the prompt from graph/orchestrator, let's identify the content structure.
    # Typically, the prompt has sections: FAKTA KNOWLEDGE GRAPH, KONTEKS ATTACHMENT, BUKTI EKSTERNAL, RIWAYAT PERCAKAPAN.
    # Let's write a robust parser/trimmer for the message contents.
    for msg in fitted:
        if msg.get("role") == "system":
            continue
        content = str(msg.get("content", ""))

        # Discard microscopic description / protein targets not requested / IUPAC on persona Umum from facts
        # We can do basic string trimming / cleaning if they exist in the content
        if "FAKTA KNOWLEDGE GRAPH:" in content:
            content = _trim_facts_content(content, persona, user_query)

        # Truncate oldest history or extra evidence lines if still too large
        lines = content.split("\n")
        while estimate_tokens("\n".join(lines)) > budget.input_budget and len(lines) > 5:
            # Pop lines from the bottom (which contains evidence or oldest parts) or trim content
            lines.pop(len(lines) // 2)

        msg["content"] = "\n".join(lines)

    if _count(fitted) > budget.input_budget:
        # Emergency truncation of the user message (retaining core instruction/query)
        for msg in fitted:
            if msg.get("role") == "system":
                continue
            content = str(msg.get("content", ""))
            if len(content) > 1000:
                msg["content"] = content[:1000] + "\n\n[Konteks dipotong karena batas ukuran model.]"

    if _count(fitted) > budget.input_budget:
        raise AppError("MODEL_CONTEXT_OVERFLOW", "Prompt melebihi kapasitas konteks model.", 413)

    return fitted


def _trim_facts_content(content: str, persona: str, user_query: str) -> str:
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        lower_line = line.lower()
        # Discard microscopic description
        if "deskripsi mikroskopis" in lower_line:
            continue
        # Discard protein targets not requested
        if (
            "target protein" in lower_line
            and "mekanisme" not in user_query.lower()
            and "protein" not in user_query.lower()
        ):
            continue
        # Discard IUPAC on persona Umum
        if "iupac" in lower_line and persona == "umum":
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _count(messages: list[dict[str, Any]]) -> int:
    return sum(estimate_tokens(str(msg.get("content", ""))) for msg in messages)
