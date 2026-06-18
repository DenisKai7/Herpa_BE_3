import math
from typing import Any

from app.agents.safety_agent import RED_FLAGS
from app.core.exceptions import NotFoundError
from app.core.json_safety import json_safe
from app.graph.repositories import KnowledgeGraphRepository
from app.models.common import SourceReference
from app.models.recommendation import HerbalCandidate, HerbalRecommendationRequest, HerbalRecommendationResponse, RecommendationScore
from app.services.recommendation.symptom_aliases import expand_symptoms
from app.services.supabase.client import SupabaseClient

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


def extract_symptoms_from_complaint(complaint: str) -> list[str]:
    normalized = " ".join(complaint.lower().strip().split())
    if not normalized:
        return []
    for separator in (",", ";", " dengan ", " dan "):
        normalized = normalized.replace(separator, "|")
    return [item.strip() for item in normalized.split("|") if len(item.strip()) >= 3]


def resolve_safety_status(
    *, toxicity: list[str], contraindications: list[str], interactions: list[str], user_context: dict[str, Any]
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
        return "caution", "Perlu perhatian", notes

    return "unknown", "Data keamanan belum cukup", ["Data keamanan spesifik belum tersedia pada knowledge graph."]


def resolve_evidence_status(sources: list[dict[str, Any]]) -> tuple[str, str]:
    usable_sources = [source for source in sources if source]
    if not usable_sources:
        return "unavailable", "Data bukti belum tersedia"
    if len(usable_sources) < 2:
        return "limited", "Data bukti terbatas"
    return "available", "Data pendukung tersedia"


def resolve_relevance_label(score: float) -> tuple[str, str]:
    score = clamp_score(score)
    if score >= 0.75:
        return "high", "Relevansi tinggi"
    if score >= 0.50:
        return "medium", "Relevansi sedang"
    if score > 0:
        return "low", "Relevansi rendah"
    return "unknown", "Relevansi belum tersedia"


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


class RecommendationOrchestrator:
    def __init__(self, repository: KnowledgeGraphRepository, db: SupabaseClient, allow_mock: bool = False):
        self.repository = repository
        self.db = db
        self.allow_mock = allow_mock
        self._history: dict[str, list[dict]] = {}

    async def analyze(
        self, user_id: str, payload: HerbalRecommendationRequest, request_id: str
    ) -> HerbalRecommendationResponse:
        if not payload.symptoms:
            payload.symptoms = extract_symptoms_from_complaint(payload.complaint or payload.free_text)
        if not payload.free_text and payload.complaint:
            payload.free_text = payload.complaint

        expanded_symptoms = expand_symptoms(payload.symptoms)
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

        rows = await self.repository.plants_for_symptoms(expanded_symptoms or payload.symptoms, limit=8)
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

        candidates: list[HerbalCandidate] = []
        excluded: list[dict[str, Any]] = []
        low_confidence_candidates: list[HerbalCandidate] = []

        for row in rows:
            plant = row.get("plant", {})
            plant_id = plant.get("plant_id") or plant.get("herb_id") or plant.get("id") or "unknown"
            local_name = plant.get("local_name") or plant.get("commonName") or plant.get("name") or "Tidak diketahui"
            scientific_name = plant.get("scientific_name") or plant.get("canonicalScientificName") or plant.get("latinName")
            matched = _string_list(row.get("matched_symptoms"))
            related_uses = _string_list(row.get("related_uses") or row.get("therapeutic_uses") or matched)
            active_compounds = _string_list(row.get("active_compounds") or row.get("compounds"))
            toxicity = _string_list(row.get("toxicity"))
            contraindications = _string_list(row.get("contraindications"))
            interactions = _string_list(row.get("interactions"))
            side_effects = _string_list(row.get("side_effects"))
            sources_raw = _source_dicts(row, plant)

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
            )
            evidence_status, evidence_label = resolve_evidence_status(sources_raw)
            symptom_match_score = clamp_score(len(set(matched) & set(payload.symptoms)) / max(len(payload.symptoms), 1))
            if symptom_match_score == 0 and matched:
                symptom_match_score = clamp_score(len(matched) / max(len(expanded_symptoms), 1))
            alias_match_score = clamp_score(len(set(matched) & set(expanded_symptoms)) / max(len(expanded_symptoms), 1))
            compound_score = 1.0 if active_compounds else 0.0
            evidence_score = clamp_score(len(sources_raw) / 3)
            safety_score = {"unknown": 0.5, "safe": 0.8, "caution": 0.4, "unsafe": 0.0}[safety_status]
            confidence = clamp_score(
                symptom_match_score * 0.40
                + alias_match_score * 0.20
                + compound_score * 0.15
                + evidence_score * 0.15
                + safety_score * 0.10
            )
            relevance_level, relevance_label = resolve_relevance_label(confidence)
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
            if not source_refs:
                source_refs = [
                    SourceReference(
                        type="neo4j",
                        source_id=plant_id,
                        title=scientific_name or local_name,
                        evidence_level=evidence_status,
                    )
                ]

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
                warnings=[EDUCATIONAL_WARNING],
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
                trusted_source_coverage_score=evidence_score,
                model_assisted_coverage_score=0.0,
                safety_coverage_score=safety_score,
                overall_verification_status="source_verified" if sources_raw else "insufficient_data",
                safety_data_status="complete" if safety_status in {"safe", "caution", "unsafe"} else "missing",
                general_safety_warnings=safety_notes,
            )
            if confidence < MIN_DISPLAY_CONFIDENCE:
                low_confidence_candidates.append(candidate)
                excluded.append({"plant_id": plant_id, "reason": "confidence terlalu rendah", "confidence": confidence})
            else:
                candidates.append(candidate)

        if not candidates and low_confidence_candidates:
            candidates = low_confidence_candidates[:1]
            excluded = [item for item in excluded if item.get("plant_id") != candidates[0].plant_id]

        status = "completed" if candidates else "no_fully_verified_candidate"
        limitations = [] if candidates else [NO_HERBAL_MATCH_WARNING]
        warnings = [] if candidates else [NO_HERBAL_MATCH_WARNING]
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
            total_candidates_found=len(rows),
            total_candidates_eligible=len(candidates),
            total_candidates_excluded=len(excluded),
            metadata={"knowledge_graph_checked": True, "candidate_count": len(candidates), "expanded_symptoms": expanded_symptoms},
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
        return response

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
