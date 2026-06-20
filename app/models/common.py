from typing import Any, Generic, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T
    meta: Meta = Field(default_factory=Meta)


class SourceReference(BaseModel):
    type: str = "neo4j"
    source_id: str | None = None
    title: str | None = None
    identifier: str | None = None
    year: int | str | None = None
    evidence_level: str | None = None
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
