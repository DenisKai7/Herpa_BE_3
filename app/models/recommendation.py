from typing import Any, Literal
from pydantic import BaseModel, Field
from app.models.common import SourceReference


class HerbalRecommendationRequest(BaseModel):
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    free_text: str = Field(default="", max_length=5000)
    duration: str | None = None
    severity: Literal["ringan", "sedang", "berat"] | None = None
    age_group: Literal["child", "adolescent", "adult", "elderly"] | None = None
    sex: Literal["female", "male", "other", "unknown"] | None = None
    pregnant: bool = False
    breastfeeding: bool = False
    allergies: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    persona: str | None = None


class HerbalCandidate(BaseModel):
    plant_id: str
    local_name: str
    scientific_name: str
    relevance_score: float = Field(ge=0, le=1)
    reason: str
    plant_part: str | None = None
    evidence_level: str = "unknown"
    traditional_use: str | None = None
    preparation_note: str | None = None
    contraindications: list[str] = Field(default_factory=list)
    drug_interactions: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    field_evidence: dict[str, Any] = Field(default_factory=dict)


class HerbalRecommendationResponse(BaseModel):
    status: str
    request_id: str | None = None
    recommendations: list[HerbalCandidate] = Field(default_factory=list)
    options: list[HerbalCandidate] = Field(default_factory=list)
    excluded_candidates: list[dict[str, Any]] = Field(default_factory=list)
    general_disclaimer: str = (
        "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
    )
    disclaimer: str = "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
    medical_attention_message: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    when_to_seek_medical_help: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
