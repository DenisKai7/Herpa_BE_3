from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.common import SourceReference


class AgeGroup(StrEnum):
    CHILD = "child"
    TEEN = "teen"
    ADULT = "adult"
    ELDERLY = "elderly"


class HerbalRecommendationRequest(BaseModel):
    complaint: str = Field(
        default="",
        min_length=0,
        max_length=1000,
        description="Keluhan utama user.",
    )
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
    warnings: list[str] = Field(default_factory=list)
    safety_note: str = "Informasi ini bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan."
    metadata: dict[str, Any] = Field(default_factory=dict)
