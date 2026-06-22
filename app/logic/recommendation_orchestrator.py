import asyncio
import logging
import math
import time
from typing import Any

from app.agents.safety_agent import RED_FLAGS
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.json_safety import json_safe
from app.graph.repositories import KnowledgeGraphRepository
from app.models.common import SourceReference
from app.models.recommendation import (
    HerbEnrichmentDetail,
    HerbalCandidate,
    HerbalRecommendationRequest,
    HerbalRecommendationResponse,
    RecommendationScore,
)
from app.services.recommendation.enrichment_mapper import empty_enrichment, filter_by_persona
from app.services.recommendation.symptom_aliases import expand_symptoms
from app.services.recommendation.symptom_expander import extract_recommendation_terms
from app.services.supabase.client import SupabaseClient

logger = logging.getLogger(__name__)

MOCK_PLANTS = {
    "mual": {
        "plant_id": "plant:zingiber_officinale",
        "local_name": "Jahe",
        "scientific_name": "Zingiber officinale",
        "part": "rimpang",
        "reason": "Secara tradisional digunakan untuk membantu mual ringan.",
        "evidence": "limited_clinical",
    },
    "kembung": {
        "plant_id": "plant:zingiber_officinale",
        "local_name": "Jahe",
        "scientific_name": "Zingiber officinale",
        "part": "rimpang",
        "reason": "Dapat dipertimbangkan untuk keluhan pencernaan ringan berdasarkan data yang tersedia.",
        "evidence": "traditional",
    },
}

NO_HERBAL_MATCH_WARNING = "Data knowledge graph belum menemukan rekomendasi herbal yang cukup kuat untuk keluhan ini."
EDUCATIONAL_WARNING = "Gunakan informasi ini sebagai edukasi awal, bukan pengganti pemeriksaan tenaga kesehatan."
COUGH_RED_FLAGS = [
    "sesak napas",
    "nyeri dada",
    "batuk darah",
    "demam tinggi",
    "demam lebih dari 3 hari",
    "batuk lebih dari 2 minggu",
    "berat badan turun",
    "anak kecil",
    "hamil",
]
COUGH_MEDICAL_ADVICE = (
    "Segera periksa ke tenaga kesehatan jika batuk disertai sesak napas, demam tinggi, nyeri dada, "
    "dahak berdarah, atau berlangsung lebih dari 3 hari."
)
MIN_DISPLAY_CONFIDENCE = 0.20
MIN_STRONG_CONFIDENCE = 0.50


def clamp_score(value: object, default: float = 0.0) -> float:
    if value is None or not isinstance(value, int | float):
        return default
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        return default
    return max(0.0, min(number, 1.0))


def score_to_percent(value: float) -> int:
    return round(clamp_score(value) * 100)


def relevance_level_from_score(score: float) -> tuple[str, str]:
    score = clamp_score(score)
    if score >= 0.75:
        return "high", "Relevansi tinggi"
    if score >= 0.50:
        return "medium", "Relevansi sedang"
    if score >= 0.25:
        return "low", "Relevansi rendah"
    if score > 0:
        return "initial", "Kandidat awal"
    return "unknown", "Relevansi belum tersedia"


def extract_symptoms_from_complaint(complaint: str) -> list[str]:
    normalized = " ".join(complaint.lower().strip().split())
    if not normalized:
        return []
    for separator in (",", ";", " dengan ", " dan "):
        normalized = normalized.replace(separator, "|")
    return [item.strip() for item in normalized.split("|") if len(item.strip()) >= 3]


def resolve_safety_label(status: str | None) -> str:
    if status == "safe":
        return "Relatif aman"
    if status == "limited":
        return "Data keamanan terbatas"
    if status == "caution":
        return "Perlu perhatian"
    if status == "unsafe":
        return "Tidak disarankan"
    return "Data keamanan belum cukup"


def resolve_safety_status(
    *,
    toxicity: list[str],
    contraindications: list[str],
    interactions: list[str],
    user_context: dict[str, Any],
    initial_status: str = "unknown",
) -> tuple[str, str, list[str]]:
    notes: list[str] = []
    notes.extend(toxicity)
    notes.extend(contraindications)
    notes.extend(interactions)

    pregnant = bool(user_context.get("pregnant")) or user_context.get("pregnancy_status") == "pregnant"
    if pregnant and any("hamil" in note.lower() or "pregnan" in note.lower() for note in notes):
        return "unsafe", "Tidak aman", ["Kontraindikasi jelas terkait kehamilan.", *notes]

    serious_terms = ("serius", "berat", "toksik kuat", "fatal", "dilarang")
    if any(any(term in note.lower() for term in serious_terms) for note in notes):
        return "unsafe", "Tidak aman", notes

    if notes:
        # Check if there's any explicit safe statements or non-toxic flags which might conflict,
        # but negative safety notes take precedence.
        return "caution", "Perlu perhatian", notes

    if initial_status in ("safe", "limited", "caution", "unsafe"):
        return initial_status, resolve_safety_label(initial_status), ["Status keamanan terdata pada knowledge graph."]

    return "unknown", "Data keamanan belum cukup", ["Data keamanan spesifik belum tersedia pada knowledge graph."]


def resolve_evidence_status(
    sources: list[dict[str, Any]] | None = None,
    traditional_uses: list[Any] | None = None,
    claims: list[Any] | None = None,
) -> tuple[str, str]:
    usable_sources = [source for source in sources or [] if source]
    if usable_sources:
        return "available", "Data sumber tersedia"
    if claims:
        return "limited", "Data klaim tersedia"
    if traditional_uses:
        return "traditional", "Data tradisional tersedia"
    return "unavailable", "Data bukti belum tersedia"


def resolve_data_status(candidate: dict[str, Any]) -> tuple[str, str]:
    """Determine factual data status label for a recommendation card."""
    has_traditional = bool(candidate.get("traditional_uses"))
    has_compounds = bool(candidate.get("active_compounds"))
    has_sources = bool(candidate.get("evidence_sources") or candidate.get("sources"))
    has_detail = bool(candidate.get("has_detail_data"))

    if has_sources:
        return "source_available", "Data sumber tersedia"
    if has_traditional and has_compounds:
        return "kg_supported", "Didukung data knowledge graph"
    if has_traditional:
        return "traditional_available", "Data tradisional tersedia"
    if has_compounds:
        return "compound_available", "Data senyawa tersedia"
    if has_detail:
        return "detail_available", "Data detail tersedia"
    return "limited", "Data masih terbatas"


def resolve_relevance_label(score: float) -> tuple[str, str]:
    """Alias for relevance_level_from_score — kept for backward compatibility."""
    return relevance_level_from_score(score)


def build_recommendation_explanation(
    *, local_name: str, symptoms: list[str], related_uses: list[str], confidence: float
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if related_uses:
        reasons.append("Knowledge graph menghubungkan tanaman ini dengan penggunaan: " + ", ".join(related_uses[:3]) + ".")
    if symptoms:
        reasons.append("Keluhan yang dianalisis: " + ", ".join(symptoms) + ".")
    if not reasons:
        reasons.append("Tanaman ini muncul sebagai kandidat awal, tetapi alasan spesifik belum cukup kuat pada data saat ini.")

    if confidence >= MIN_STRONG_CONFIDENCE:
        explanation = (
            f"{local_name} muncul sebagai kandidat karena memiliki relasi penggunaan herbal yang cukup relevan "
            "dengan keluhan yang dimasukkan."
        )
    else:
        explanation = (
            f"{local_name} muncul sebagai kandidat awal, tetapi relevansinya masih rendah sehingga perlu verifikasi lebih lanjut."
        )
    return explanation, reasons


def build_light_explanation(candidate: dict[str, Any], score: float) -> str:
    plant = candidate.get("plant") or {}
    local_name = candidate.get("local_name") or plant.get("local_name") or "Tanaman ini"
    if score >= 0.5:
        return (
            f"{local_name} muncul sebagai kandidat karena memiliki kecocokan "
            "dengan gejala yang dimasukkan dan memiliki data pendukung pada knowledge graph."
        )
    return (
        f"{local_name} muncul sebagai kandidat awal, tetapi relevansinya masih rendah "
        "sehingga perlu verifikasi lebih lanjut sebelum digunakan sebagai acuan."
    )


def build_match_reasons(candidate: dict[str, Any]) -> list[str]:
    reasons = []
    symptoms = candidate.get("matched_symptoms") or []
    compounds = candidate.get("active_compounds") or []
    traditional_uses = candidate.get("traditional_uses") or []

    if symptoms:
        reasons.append("Terkait dengan gejala: " + ", ".join(symptoms[:3]) + ".")
    if traditional_uses:
        reasons.append("Memiliki data penggunaan tradisional yang relevan pada knowledge graph.")
    if compounds:
        reasons.append("Memiliki data senyawa aktif yang tercatat pada knowledge graph.")
    if not reasons:
        reasons.append("Kandidat ditemukan dari pencocokan awal, tetapi data pendukung masih terbatas.")
    return reasons


def detect_cough_red_flags(text: str) -> list[str]:
    lowered = text.lower()
    flags = [flag for flag in COUGH_RED_FLAGS if flag in lowered]
    flags.extend(message for term, message in RED_FLAGS.items() if term in lowered)
    return list(dict.fromkeys(flags))


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("name") or item.get("title") or item.get("label")
                if name:
                    result.append(str(name))
            elif item:
                result.append(str(item))
        return result
    return [str(value)]


def _source_dicts(row: dict[str, Any], plant: dict[str, Any]) -> list[dict[str, Any]]:
    raw_sources = row.get("sources") or row.get("evidence") or []
    if not raw_sources and (plant.get("evidence") or plant.get("evidence_level")):
        raw_sources = [{"type": "neo4j", "title": plant.get("evidence") or plant.get("evidence_level")}]
    sources = []
    for source in raw_sources:
        if isinstance(source, dict):
            sources.append(source)
        elif source:
            sources.append({"type": "neo4j", "title": str(source)})
    return sources


def _normalize_recommendation_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("plant"):
        return row
    plant_id = row.get("herb_id") or row.get("plant_id") or row.get("id") or "unknown"
    return {
        **row,
        "plant": {
            "plant_id": plant_id,
            "herb_id": plant_id,
            "local_name": row.get("local_name") or row.get("common_name") or row.get("commonName"),
            "scientific_name": row.get("scientific_name") or row.get("canonicalScientificName") or row.get("latinName"),
            "safety_status": row.get("safety_status"),
        },
    }


def _enrichment_strings(enrichment: dict[str, Any], key: str, *fields: str) -> list[str]:
    values = []
    for item in enrichment.get(key, []) or []:
        if not isinstance(item, dict):
            continue
        for field in fields:
            value = item.get(field)
            if value:
                values.append(str(value))
                break
    return values


class RecommendationOrchestrator:
    def __init__(self, repository: KnowledgeGraphRepository, db: SupabaseClient, allow_mock: bool = False):
        self.repository = repository
        self.db = db
        self.allow_mock = allow_mock
        self.settings = get_settings()
        self._history: dict[str, list[dict]] = {}

    async def analyze(
        self, user_id: str, payload: HerbalRecommendationRequest, request_id: str
    ) -> HerbalRecommendationResponse:
        if not payload.symptoms:
            payload.symptoms = extract_symptoms_from_complaint(payload.complaint or payload.free_text)
        if not payload.free_text and payload.complaint:
            payload.free_text = payload.complaint

        term_result = extract_recommendation_terms(payload.complaint or payload.free_text, payload.symptoms)
        primary_terms = term_result.primary_terms
        expanded_symptoms = term_result.expanded_terms or expand_symptoms(payload.symptoms)
        all_text = " ".join(payload.symptoms + [payload.free_text, payload.complaint]).lower()
        red = detect_cough_red_flags(all_text)
        if payload.severity == "berat":
            red.append("Keluhan berat memerlukan evaluasi tenaga kesehatan.")
        if red:
            return HerbalRecommendationResponse(
                status="medical_attention_recommended",
                request_id=request_id,
                complaint=payload.complaint,
                normalized_complaint=payload.complaint.lower(),
                symptoms=payload.symptoms,
                red_flags=red,
                medical_attention_message="Segera konsultasi ke tenaga kesehatan untuk keluhan berisiko.",
                when_to_seek_medical_help=red,
            )

        logger.info("herbal_recommendation_stage", extra={"stage": "start"})
        query_terms = expanded_symptoms or payload.symptoms
        logger.info(
            "herbal_recommendation_stage",
            extra={"stage": "terms_expanded", "term_count": len(query_terms), "primary_count": len(primary_terms)},
        )
        max_candidates = self.settings.herbal_recommendation_max_candidates
        query_started = time.perf_counter()
        if self.settings.herbal_recommendation_light_analyze:
            if hasattr(self.repository, "recommend_herbs_light_v3"):
                rows = await self.repository.recommend_herbs_light_v3(
                    primary_terms=primary_terms,
                    expanded_terms=query_terms,
                    limit=max_candidates,
                )
            else:
                rows = await self.repository.recommend_herbs_light(query_terms, limit=max_candidates)
        else:
            try:
                rows = await self.repository.recommend_herbs_by_symptoms(query_terms, limit=max_candidates)
            except Exception:
                rows = []
            if not rows:
                rows = await self.repository.recommend_herbs_legacy(query_terms, limit=max_candidates)
        duration_ms = int((time.perf_counter() - query_started) * 1000)
        logger.info(
            "herbal_recommendation_stage",
            extra={"stage": "light_candidates_loaded", "candidate_count": len(rows), "duration_ms": duration_ms},
        )
        rows = [_normalize_recommendation_row(row) for row in rows]
        if not rows and self.allow_mock:
            seen = set()
            rows = []
            for symptom in payload.symptoms:
                item = MOCK_PLANTS.get(symptom.lower())
                if item and item["plant_id"] not in seen:
                    rows.append(
                        {
                            "plant": item,
                            "matched_symptoms": [symptom],
                            "contraindications": [],
                            "side_effects": [],
                            "interactions": [],
                            "evidence": [],
                            "compounds": [],
                            "sources": [],
                            "toxicity": [],
                        }
                    )
                    seen.add(item["plant_id"])

        if self.settings.herbal_recommendation_lazy_detail:
            enrichment_results: list[dict[str, Any] | BaseException] = [empty_enrichment() for _ in rows]
        else:
            semaphore = asyncio.Semaphore(self.settings.herbal_recommendation_detail_parallelism)

            async def safe_detail(row: dict[str, Any]) -> dict[str, Any]:
                async with semaphore:
                    plant = row.get("plant") or {}
                    herb_id = plant.get("plant_id") or row.get("herb_id")
                    try:
                        return await self.repository.get_herb_detail_core(str(herb_id))
                    except Exception:
                        logger.exception("safe_get_detail_failed", extra={"herb_id": herb_id})
                        return empty_enrichment()

            enrichment_results = await asyncio.gather(*[safe_detail(row) for row in rows], return_exceptions=True)

        candidates: list[HerbalCandidate] = []
        excluded: list[dict[str, Any]] = []
        low_confidence_candidates: list[HerbalCandidate] = []

        for row, raw_enrichment in zip(rows, enrichment_results, strict=False):
            if isinstance(raw_enrichment, BaseException) or not isinstance(raw_enrichment, dict):
                enrichment = empty_enrichment()
            else:
                enrichment = filter_by_persona(raw_enrichment, payload.persona)
            plant = row.get("plant", {})
            plant_id = plant.get("plant_id") or plant.get("herb_id") or plant.get("id") or "unknown"
            local_name = plant.get("local_name") or plant.get("commonName") or plant.get("name") or "Tidak diketahui"
            scientific_name = plant.get("scientific_name") or plant.get("canonicalScientificName") or plant.get("latinName")
            matched = _string_list(row.get("matched_symptoms"))
            related_uses = _string_list(row.get("related_uses") or row.get("therapeutic_uses") or matched)
            active_compounds = _string_list(row.get("active_compounds") or row.get("compounds"))
            toxicity = _string_list(row.get("toxicity"))
            contraindications = _string_list(row.get("contraindications")) + _enrichment_strings(
                enrichment, "contraindications", "condition", "description"
            )
            interactions = _string_list(row.get("interactions")) + _enrichment_strings(
                enrichment, "drug_interactions", "substance", "description"
            )
            side_effects = _string_list(row.get("side_effects"))
            safety_warning_texts = _enrichment_strings(enrichment, "safety_warnings", "title", "description")
            if safety_warning_texts:
                toxicity.extend(safety_warning_texts)
            sources_raw = _source_dicts(row, plant)
            for section in (
                "traditional_uses",
                "preparation_methods",
                "usage_guidelines",
                "safety_warnings",
                "clinical_guidelines",
                "claims",
            ):
                for item in enrichment.get(section, []) or []:
                    if isinstance(item, dict):
                        item_sources = item.get("sources")
                        if isinstance(item_sources, list):
                            sources_raw.extend([source for source in item_sources if isinstance(source, dict)])

            conflicts = [
                c for c in payload.medical_conditions if any(c.lower() in note.lower() for note in contraindications)
            ] + [m for m in payload.current_medications if any(m.lower() in note.lower() for note in interactions)]
            if payload.pregnant and any("hamil" in note.lower() for note in contraindications):
                conflicts.append("kehamilan")
            if conflicts:
                excluded.append({"plant_id": plant_id, "reason": "Konflik keamanan terdeteksi", "conflicts": conflicts})
                continue

            safety_status, safety_label, safety_notes = resolve_safety_status(
                toxicity=toxicity,
                contraindications=contraindications,
                interactions=interactions,
                user_context={"pregnant": payload.pregnant, "pregnancy_status": payload.pregnancy_status},
                initial_status=row.get("safety_status") or plant.get("safety_status") or "unknown",
            )
            row_traditional_uses = row.get("traditional_uses") or []
            evidence_status, evidence_label = resolve_evidence_status(
                sources_raw,
                traditional_uses=row_traditional_uses or enrichment.get("traditional_uses"),
                claims=enrichment.get("claims"),
            )
            if self.settings.herbal_recommendation_light_analyze and "score" in row:
                confidence = clamp_score(row.get("score"))
                symptom_match_score = clamp_score(row.get("primary_coverage_score"))
                alias_match_score = clamp_score(row.get("expanded_coverage_score"))
                compound_score = clamp_score(row.get("compound_score"))
                evidence_score = 1.0 if evidence_status == "available" else 0.6 if evidence_status in {"traditional", "limited"} else 0.0
                safety_score = clamp_score(row.get("safety_score"))
            else:
                symptom_match_score = clamp_score(len(set(matched) & set(payload.symptoms)) / max(len(payload.symptoms), 1))
                alias_match_score = clamp_score(len(set(matched) & set(expanded_symptoms)) / max(len(expanded_symptoms), 1))
                compound_score = min(len(active_compounds) / 5, 1.0)
                evidence_score = clamp_score(len(sources_raw) / 3)
                safety_score = {"unknown": 0.6, "safe": 1.0, "caution": 0.3, "unsafe": 0.0}.get(safety_status, 0.5)
                confidence = clamp_score(
                    symptom_match_score * 0.45
                    + alias_match_score * 0.15
                    + compound_score * 0.10
                    + evidence_score * 0.15
                    + safety_score * 0.15
                )
            relevance_level, relevance_label = resolve_relevance_label(confidence)
            relevance_percent = score_to_percent(confidence)
            symptom_coverage_percent = score_to_percent(symptom_match_score)
            # Resolve factual data status
            data_status_input = {
                "traditional_uses": row_traditional_uses or enrichment.get("traditional_uses"),
                "active_compounds": active_compounds,
                "evidence_sources": sources_raw,
                "sources": sources_raw,
                "has_detail_data": bool(enrichment.get("traditional_uses") or enrichment.get("preparation_methods")),
            }
            data_status, data_status_label = resolve_data_status(data_status_input)
            if self.settings.herbal_recommendation_light_analyze and "score" in row:
                explanation = build_light_explanation(row, confidence)
                match_reasons = build_match_reasons(row)
            else:
                explanation, match_reasons = build_recommendation_explanation(
                    local_name=local_name,
                    symptoms=payload.symptoms,
                    related_uses=related_uses,
                    confidence=confidence,
                )
            scores = RecommendationScore(
                confidence=confidence,
                relevance_score=confidence,
                symptom_match_score=symptom_match_score,
                evidence_score=evidence_score,
                compound_score=compound_score,
                safety_score=safety_score,
                alias_match_score=alias_match_score,
                graph_coverage=symptom_match_score,
                trusted_source_coverage=evidence_score,
                model_assisted_coverage=0.0,
                safety_coverage=safety_score,
            )
            source_refs = [
                SourceReference(
                    type=str(source.get("type") or "neo4j"),
                    source_id=str(source.get("source_id") or source.get("id") or source.get("identifier") or plant_id),
                    title=str(source.get("title") or source.get("name") or scientific_name or local_name),
                    evidence_level=str(source.get("evidence_level") or source.get("level") or evidence_status),
                )
                for source in sources_raw[:5]
            ]

            candidate_warnings = [EDUCATIONAL_WARNING]
            if safety_status == "caution":
                candidate_warnings.extend(safety_notes)

            candidate = HerbalCandidate(
                plant_id=plant_id,
                herb_id=plant_id,
                canonical_key=(scientific_name or local_name).lower(),
                local_name=local_name,
                scientific_name=scientific_name or "Tidak tersedia",
                confidence=confidence,
                relevance_score=confidence,
                recommendation_score=confidence,
                symptom_coverage=symptom_match_score,
                relevance_level=relevance_level,
                relevance_status="exact_match" if symptom_match_score >= 0.99 else "partial_match" if symptom_match_score >= 0.5 else "low_relevance",
                relevance_label=relevance_label,
                relevance_percent=relevance_percent,
                symptom_coverage_percent=symptom_coverage_percent,
                data_status=data_status,
                data_status_label=data_status_label,
                safety_status=safety_status,
                safety_label=safety_label,
                safety_notes=safety_notes,
                evidence_status=evidence_status,
                evidence_label=evidence_label,
                evidence_sources=sources_raw,
                explanation=explanation,
                recommendation_reason=explanation,
                reason=explanation,
                match_reasons=match_reasons,
                related_symptoms=related_uses or matched,
                active_compounds=active_compounds,
                warnings=candidate_warnings,
                limitations=[] if confidence >= MIN_STRONG_CONFIDENCE else ["Relevansi masih terbatas; gunakan sebagai informasi awal."],
                scores=scores,
                plant_part=plant.get("part") or plant.get("plant_part"),
                evidence_level=evidence_status,
                traditional_use=plant.get("traditional_use"),
                preparation_note=plant.get("preparation_note"),
                contraindications=contraindications,
                drug_interactions=interactions,
                side_effects=side_effects,
                sources=source_refs,
                graph_coverage_score=symptom_match_score,
                primary_coverage_score=symptom_match_score,
                expanded_coverage_score=alias_match_score,
                traditional_use_score=clamp_score(row.get("traditional_use_score")),
                trusted_source_coverage_score=evidence_score,
                model_assisted_coverage_score=0.0,
                safety_coverage_score=safety_score,
                overall_verification_status="source_verified" if sources_raw else "insufficient_data",
                safety_data_status="complete" if safety_status in {"safe", "caution", "unsafe"} else "limited",
                general_safety_warnings=safety_notes,
                enrichment=HerbEnrichmentDetail.model_validate(enrichment),
                traditional_uses=enrichment.get("traditional_uses", []) or [{"title": title} for title in _string_list(row.get("traditional_uses"))],
                preparation_methods=enrichment.get("preparation_methods", []),
                usage_guidelines=enrichment.get("usage_guidelines", []),
                safety_warnings=enrichment.get("safety_warnings", []),
                plant_parts=enrichment.get("plant_parts", []),
                storage_guidelines=enrichment.get("storage_guidelines", []),
                myth_facts=enrichment.get("myth_facts", []),
                quality_standards=enrichment.get("quality_standards", []),
                clinical_guidelines=enrichment.get("clinical_guidelines", []),
                drug_interactions_detail=enrichment.get("drug_interactions", []),
                contraindications_detail=enrichment.get("contraindications", []),
                pharmacokinetic_profiles=enrichment.get("pharmacokinetic_profiles", []),
                research_topics=enrichment.get("research_topics", []),
                claims=enrichment.get("claims", []),
                related_symptom_details=enrichment.get("related_symptoms", []),
            )
            if confidence < MIN_DISPLAY_CONFIDENCE:
                low_confidence_candidates.append(candidate)
                excluded.append({"plant_id": plant_id, "reason": "confidence terlalu rendah", "confidence": confidence})
            else:
                candidates.append(candidate)

        if not candidates and low_confidence_candidates:
            candidates = low_confidence_candidates[:1]
            excluded = [item for item in excluded if item.get("plant_id") != candidates[0].plant_id]

        status = "completed"
        limitations = [] if candidates else ["Data rekomendasi masih terbatas dan perlu pengayaan lebih lanjut."]
        warnings = []
        suggested_terms: list[str] = []
        if not candidates:
            warnings.append(
                "Belum ditemukan kandidat herbal yang cukup relevan pada knowledge graph untuk keluhan ini."
            )
            suggested_terms = expanded_symptoms[:5] if expanded_symptoms else primary_terms[:5]
            if not suggested_terms:
                suggested_terms = payload.symptoms[:3]
            limitations.append(
                "Keluhan awam mungkin perlu dipetakan ke istilah yang lebih spesifik. "
                "Coba gunakan istilah lain seperti: " + ", ".join(suggested_terms[:3]) + "."
            )
        elif any(c.safety_status == "caution" for c in candidates):
            warnings.append("Beberapa kandidat herbal memerlukan perhatian khusus (caution) sebelum digunakan.")
        medical_advice = [COUGH_MEDICAL_ADVICE] if any("batuk" in item or "tenggorokan" in item for item in payload.symptoms) else []
        response = HerbalRecommendationResponse(
            status=status,
            request_id=request_id,
            complaint=payload.complaint,
            normalized_complaint=payload.complaint.lower(),
            symptoms=payload.symptoms,
            extracted_symptoms=payload.symptoms,
            recommendations=candidates,
            options=candidates,
            excluded_candidates=excluded,
            red_flags=[],
            when_to_seek_medical_help=medical_advice,
            limitations=limitations,
            warnings=warnings,
            suggested_terms=suggested_terms,
            total_candidates_found=len(rows),
            total_candidates_eligible=len(candidates),
            total_candidates_excluded=len(excluded),
            metadata={
                "knowledge_graph_checked": True,
                "candidate_count": len(candidates),
                "primary_terms": primary_terms,
                "expanded_symptoms": expanded_symptoms,
                "light_query_duration_ms": duration_ms,
            },
        )
        if self.allow_mock:
            self._history.setdefault(user_id, []).append(
                {
                    "id": request_id,
                    "user_id": user_id,
                    "input": json_safe(payload.model_dump(mode="python")),
                    "response": json_safe(response.model_dump(mode="python")),
                }
            )
        else:
            rows = await self.db.insert(
                "recommendation_sessions",
                json_safe(
                    {
                        "user_id": user_id,
                        "input": payload.model_dump(mode="python"),
                        "status": status,
                        "red_flags": red,
                        "limitations": limitations,
                    }
                ),
            )
            session_id = rows[0]["id"]
            for candidate in candidates:
                await self.db.insert(
                    "recommendation_results",
                    json_safe(
                        {
                            "session_id": session_id,
                            "plant_id": candidate.plant_id,
                            "local_name": candidate.local_name,
                            "scientific_name": candidate.scientific_name,
                            "relevance_score": candidate.relevance_score,
                            "result": candidate.model_dump(mode="python"),
                        }
                    ),
                )
            response.metadata["session_id"] = session_id
        logger.info(
            "herbal_recommendation_stage",
            extra={"stage": "response_built", "count": len(candidates)},
        )
        return response

    async def get_herb_recommendation_detail(self, herb_id: str, persona: str = "umum") -> dict[str, Any]:
        detail = await self.repository.get_herb_detail_core(herb_id)
        return filter_by_persona(detail, persona)

    async def history(self, user_id: str) -> list[dict]:
        if self.allow_mock:
            return list(reversed(self._history.get(user_id, [])))
        return await self.db.select(
            "recommendation_sessions",
            {"select": "*,recommendation_results(*)", "user_id": f"eq.{user_id}", "order": "created_at.desc"},
        )

    async def get(self, user_id: str, session_id: str) -> dict:
        if self.allow_mock:
            for row in self._history.get(user_id, []):
                if row["id"] == session_id:
                    return row
            raise NotFoundError("Riwayat rekomendasi tidak ditemukan.")
        rows = await self.db.select(
            "recommendation_sessions",
            {"select": "*,recommendation_results(*)", "id": f"eq.{session_id}", "user_id": f"eq.{user_id}", "limit": "1"},
        )
        if not rows:
            raise NotFoundError("Riwayat rekomendasi tidak ditemukan.")
        return rows[0]

    async def delete(self, user_id: str, session_id: str) -> None:
        await self.get(user_id, session_id)
        if self.allow_mock:
            self._history[user_id] = [x for x in self._history.get(user_id, []) if x["id"] != session_id]
        else:
            await self.db.delete("recommendation_sessions", {"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
