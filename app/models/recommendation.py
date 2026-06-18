from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.json_safety import json_safe
from app.models.common import SourceReference

SafetyStatus = Literal["safe", "caution", "unsafe", "unknown"]
EvidenceStatus = Literal["available", "limited", "unavailable", "unknown"]
RelevanceLevel = Literal["high", "medium", "low", "unknown"]


class AgeGroup(StrEnum):
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"
    ELDERLY = "elderly"


class RecommendationScore(BaseModel):
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    symptom_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    compound_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_score: float = Field(default=0.0, ge=0.0, le=1.0)
    alias_match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    graph_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    trusted_source_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    model_assisted_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_coverage: float = Field(default=0.0, ge=0.0, le=1.0)


class HerbalRecommendationRequest(BaseModel):
    complaint: str = Field(default="", min_length=0, max_length=1000, description="Keluhan utama user.")
    symptoms: list[str] = Field(default_factory=list, max_length=20)
    free_text: str = Field(default="", max_length=5000)
    duration: str | None = None
    severity: Literal["ringan", "sedang", "berat"] | None = None
    age_group: AgeGroup | None = None
    sex: Literal["female", "male", "other", "unknown"] | None = None
    pregnant: bool = False
    breastfeeding: bool = False
    pregnancy_status: str | None = None
    allergies: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    medical_conditions: list[str] = Field(default_factory=list)
    chronic_conditions: list[str] = Field(default_factory=list)
    persona: str = "umum"
    model_choice: str = "fast-medium"

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_payload(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        normalized = dict(data)
        if "complaint" not in normalized:
            for key in ("keluhan", "main_complaint", "query", "message", "text"):
                if normalized.get(key):
                    normalized["complaint"] = normalized[key]
                    break
        if "complaint" not in normalized and normalized.get("free_text"):
            normalized["complaint"] = normalized["free_text"]
        if "free_text" not in normalized and normalized.get("complaint"):
            normalized["free_text"] = normalized["complaint"]
        if "persona" not in normalized and normalized.get("ai_mode"):
            normalized["persona"] = normalized["ai_mode"]
        if "model_choice" not in normalized and normalized.get("mode"):
            normalized["model_choice"] = normalized["mode"]
        if normalized.get("model_choice") in ("thinking-hard", "thinking_hard", "thinking", "hard"):
            normalized["model_choice"] = "thinking-high"
        if "medical_conditions" not in normalized and normalized.get("chronic_conditions") is not None:
            normalized["medical_conditions"] = normalized["chronic_conditions"]
        return normalized

    @model_validator(mode="after")
    def ensure_complaint_source(self) -> "HerbalRecommendationRequest":
        if not self.complaint and self.free_text:
            self.complaint = self.free_text
        if not self.free_text and self.complaint:
            self.free_text = self.complaint
        if len(self.complaint) < 3 and not self.symptoms:
            raise ValueError("Keluhan utama terlalu pendek.")
        return self

    @field_validator("complaint", "free_text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("symptoms", mode="before")
    @classmethod
    def normalize_symptoms(cls, value: Any) -> Any:
        if value in (None, "", "null", "undefined"):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allergies", "current_medications", "medical_conditions", "chronic_conditions", mode="before")
    @classmethod
    def normalize_optional_lists(cls, value: Any) -> Any:
        if value in (None, "", "null", "undefined"):
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("age_group", mode="before")
    @classmethod
    def normalize_age_group(cls, value: Any) -> Any:
        if value in (None, "", "null", "undefined", "unknown"):
            return None
        normalized = str(value).strip().lower()
        mapping = {
            "anak": "child",
            "anak-anak": "child",
            "child": "child",
            "children": "child",
            "infant": "child",
            "bayi": "child",
            "remaja": "teen",
            "teen": "teen",
            "teenager": "teen",
            "adolescent": "teen",
            "dewasa": "adult",
            "adult": "adult",
            "adults": "adult",
            "lansia": "elderly",
            "lanjut usia": "elderly",
            "elderly": "elderly",
            "senior": "elderly",
            "tua": "elderly",
        }
        return mapping.get(normalized, normalized)

    @field_validator("pregnancy_status", mode="before")
    @classmethod
    def normalize_pregnancy_status(cls, value: Any) -> Any:
        if value in (None, "", "null", "undefined", "unknown"):
            return None
        normalized = str(value).strip().lower()
        mapping = {
            "tidak": "not_pregnant",
            "tidak hamil": "not_pregnant",
            "not_pregnant": "not_pregnant",
            "hamil": "pregnant",
            "pregnant": "pregnant",
            "menyusui": "breastfeeding",
            "breastfeeding": "breastfeeding",
            "tidak tahu": "unknown",
            "unknown": "unknown",
        }
        return mapping.get(normalized, normalized)


class HerbalCandidate(BaseModel):
    plant_id: str
    herb_id: str | None = None
    canonical_key: str | None = None
    local_name: str
    scientific_name: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendation_score: float = Field(default=0.0, ge=0.0, le=1.0)
    symptom_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    relevance_level: RelevanceLevel = "unknown"
    relevance_status: str = "unknown"
    relevance_label: str = "Relevansi belum tersedia"
    safety_status: SafetyStatus = "unknown"
    safety_label: str = "Data keamanan belum cukup"
    safety_notes: list[str] = Field(default_factory=list)
    evidence_status: EvidenceStatus = "unknown"
    evidence_label: str = "Data bukti belum tersedia"
    evidence_sources: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("evidence_sources", "field_evidence", mode="before", check_fields=False)
    @classmethod
    def sanitize_candidate_json_fields(cls, value: Any) -> Any:
        return json_safe(value)
    explanation: str = ""
    recommendation_reason: str = ""
    reason: str = ""
    match_reasons: list[str] = Field(default_factory=list)
    related_symptoms: list[str] = Field(default_factory=list)
    active_compounds: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    scores: RecommendationScore = Field(default_factory=RecommendationScore)
    plant_part: str | None = None
    evidence_level: str = "unknown"
    traditional_use: str | None = None
    preparation_note: str | None = None
    contraindications: list[str] = Field(default_factory=list)
    drug_interactions: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    field_evidence: dict[str, Any] = Field(default_factory=dict)
    graph_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trusted_source_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    model_assisted_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    safety_coverage_score: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_verification_status: str = "insufficient_data"
    safety_data_status: str = "missing"
    general_safety_warnings: list[str] = Field(default_factory=list)


class HerbalRecommendationResponse(BaseModel):
    status: str = "completed"
    request_id: str | None = None
    complaint: str = ""
    normalized_complaint: str = ""
    symptoms: list[str] = Field(default_factory=list)
    extracted_symptoms: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    total_candidates_found: int = 0
    total_candidates_eligible: int = 0
    total_candidates_excluded: int = 0
    recommendations: list[HerbalCandidate] = Field(default_factory=list)
    options: list[HerbalCandidate] = Field(default_factory=list)
    excluded_candidates: list[dict[str, Any]] = Field(default_factory=list)
    general_disclaimer: str = "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
    disclaimer: str = "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
    medical_attention_message: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    when_to_seek_medical_help: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    safety_note: str = "Informasi ini bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan."
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", "excluded_candidates", mode="before", check_fields=False)
    @classmethod
    def sanitize_response_json_fields(cls, value: Any) -> Any:
        return json_safe(value)

    @model_validator(mode="after")
    def sync_options(self) -> "HerbalRecommendationResponse":
        self.options = self.recommendations
        if not self.extracted_symptoms:
            self.extracted_symptoms = self.symptoms
        return self
