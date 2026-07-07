from typing import Any
from pydantic import BaseModel, Field


class AIUsageListParams(BaseModel):
    limit: int = Field(20, ge=1, le=200)
    offset: int = Field(0, ge=0)
    search: str | None = Field(None, max_length=200)
    user_id: str | None = None
    persona: str | None = None
    model_name: str | None = None
    endpoint: str | None = None
    provider: str | None = None
    status: str | None = None  # success/error
    date_from: str | None = None
    date_to: str | None = None
    sort: str = Field("created_at", pattern="^(created_at|latency_ms|input_tokens|output_tokens|model_name)$")
    sort_dir: str = Field("desc", pattern="^(asc|desc)$")


class AIUsageDetail(BaseModel):
    id: int
    user_id: str | None = None
    request_id: str | None = None
    model_name: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    success: bool = True
    error_code: str | None = None
    persona: str | None = None
    endpoint: str | None = None
    provider: str = "local"
    prompt_text: str | None = None
    response_text: str | None = None
    retrieval_context: Any = None
    created_at: str
    deleted_at: str | None = None
    deleted_by: str | None = None


class AIUsageDashboardStats(BaseModel):
    total_requests: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_tokens: int = 0
    active_users: int = 0
    error_rate: float = 0.0
    avg_latency_ms: float = 0.0
    active_models: int = 0
    active_personas: int = 0


class AIUsageChartsData(BaseModel):
    daily_requests: list[dict[str, Any]] = []
    daily_tokens: list[dict[str, Any]] = []
    by_persona: list[dict[str, Any]] = []
    by_model: list[dict[str, Any]] = []
    hourly_heatmap: list[dict[str, Any]] = []
    top_users: list[dict[str, Any]] = []
    top_endpoints: list[dict[str, Any]] = []
    error_analytics: dict[str, Any] = {}
    latency_stats: dict[str, Any] = {}
    cost_estimation: dict[str, Any] = {}


class AIUsageDeleteRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=100)


class AIUsageBulkDeleteByFilterRequest(BaseModel):
    user_id: str | None = None
    persona: str | None = None
    model_name: str | None = None
    endpoint: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    status: str | None = None
