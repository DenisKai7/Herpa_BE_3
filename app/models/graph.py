from typing import Any
from pydantic import BaseModel, Field


class GraphEntity(BaseModel):
    entity_type: str
    canonical_name: str
    original_text: str
    confidence: float = 1.0


class RetrievalPlan(BaseModel):
    query_type: str
    entities: list[GraphEntity] = Field(default_factory=list)
    include_evidence: bool = True
    include_safety: bool = True
    limit: int = 10


class GraphFact(BaseModel):
    source_id: str
    subject: str
    predicate: str
    object: str
    properties: dict[str, Any] = Field(default_factory=dict)
    evidence_level: str | None = None
