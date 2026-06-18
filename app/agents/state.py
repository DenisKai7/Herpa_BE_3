from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    request_id: str
    user_id: str
    application_role: str
    persona: str
    model_mode: str
    requested_mode: str
    execution_mode_used: str
    chat_id: str | None
    message_id: str | None
    user_query: str
    intent: str
    query_intent: str
    sub_intents: list[str]
    entities: list[dict[str, Any]]
    attachment_ids: list[str]
    attachment_context: list[dict[str, Any]]
    attachment_summary: dict[str, Any]
    specialist_guidance: list[str]
    graph_queries: list[dict[str, Any]]
    graph_facts: list[dict[str, Any]]
    retrieval: dict[str, Any]
    retrieval_limit: int
    compound_limit: int
    therapeutic_use_limit: int
    protein_target_limit: int
    source_limit: int
    timings: dict[str, int]
    model_call_count: int
    model_calls: int
    direct_answer_used: bool
    refinement_used: bool
    compound_count: int
    retrieval_source: str
    finish_reason: str | None
    complexity: dict[str, Any]
    external_tool_requests: list[dict[str, Any]]
    external_evidence: list[dict[str, Any]]
    safety_flags: list[str]
    red_flags: list[str]
    draft_answer: str | None
    grounded_answer: str | None
    citations: list[dict[str, Any]]
    confidence: float
    grounding_status: str
    warnings: list[str]
    tools_used: list[str]
    retrieval_count: int
    latency_ms: int
    error_code: str | None
    stage: str | None
    degraded: bool
    errors: list[dict[str, Any]]
