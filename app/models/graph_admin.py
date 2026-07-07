from typing import Any
from pydantic import BaseModel, Field


class GraphNodeCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphNodeUpdate(BaseModel):
    properties: dict[str, Any] = Field(..., min_length=1)


class GraphRelationshipCreate(BaseModel):
    source_id: int
    target_id: int
    rel_type: str = Field(..., min_length=1, max_length=100)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphBulkDelete(BaseModel):
    node_ids: list[int] = Field(..., min_length=1, max_length=100)


class GraphExportParams(BaseModel):
    label: str | None = None
    limit: int = Field(1000, ge=1, le=10000)
