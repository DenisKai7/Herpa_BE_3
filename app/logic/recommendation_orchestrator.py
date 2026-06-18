from app.graph.repositories import KnowledgeGraphRepository
from app.models.common import SourceReference
from app.models.recommendation import (
    HerbalCandidate,
    HerbalRecommendationRequest,
    HerbalRecommendationResponse,
)
from app.agents.safety_agent import RED_FLAGS
from app.services.supabase.client import SupabaseClient
from app.core.exceptions import NotFoundError

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


class RecommendationOrchestrator:
    def __init__(self, repository: KnowledgeGraphRepository, db: SupabaseClient, allow_mock: bool = False):
        self.repository = repository
        self.db = db
        self.allow_mock = allow_mock
        self._history: dict[str, list[dict]] = {}

    async def analyze(
        self, user_id: str, payload: HerbalRecommendationRequest, request_id: str
    ) -> HerbalRecommendationResponse:
        all_text = " ".join(payload.symptoms + [payload.free_text]).lower()
        red = [message for term, message in RED_FLAGS.items() if term in all_text]
        if payload.severity == "berat":
            red.append("Keluhan berat memerlukan evaluasi tenaga kesehatan.")
        if red:
            return HerbalRecommendationResponse(
                status="medical_attention_recommended",
                request_id=request_id,
                red_flags=red,
                medical_attention_message="Segera cari bantuan medis. Rekomendasi herbal tidak diberikan untuk kondisi berisiko.",
                when_to_seek_medical_help=red,
            )
        rows = await self.repository.plants_for_symptoms(payload.symptoms, limit=8)
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
                        }
                    )
                    seen.add(item["plant_id"])
        candidates = []
        excluded = []
        for row in rows:
            p = row.get("plant", {})
            contra = [str(x) for x in row.get("contraindications", []) if x]
            inter = [str(x) for x in row.get("interactions", []) if x]
            conflicts = [
                c for c in payload.medical_conditions if any(c.lower() in x.lower() for x in contra)
            ] + [m for m in payload.current_medications if any(m.lower() in x.lower() for x in inter)]
            if payload.pregnant and any("hamil" in x.lower() for x in contra):
                conflicts.append("kehamilan")
            if conflicts:
                excluded.append(
                    {
                        "plant_id": p.get("plant_id"),
                        "reason": "Konflik keamanan terdeteksi",
                        "conflicts": conflicts,
                    }
                )
                continue
            matched = row.get("matched_symptoms", [])
            score = min(0.95, 0.55 + 0.1 * len(matched))
            sources = [
                SourceReference(
                    type="neo4j",
                    source_id=p.get("plant_id", "unknown"),
                    title=p.get("scientific_name") or p.get("name") or "Tanaman",
                    evidence_level=p.get("evidence_level") or p.get("evidence") or "unknown",
                )
            ]
            candidates.append(
                HerbalCandidate(
                    plant_id=p.get("plant_id", "unknown"),
                    local_name=p.get("local_name") or p.get("name") or "Tidak diketahui",
                    scientific_name=p.get("scientific_name") or "Tidak tersedia",
                    relevance_score=score,
                    reason=p.get("reason") or f"Memiliki relasi knowledge graph dengan: {', '.join(matched)}",
                    plant_part=p.get("part") or p.get("plant_part"),
                    evidence_level=p.get("evidence_level") or p.get("evidence") or "unknown",
                    traditional_use=p.get("traditional_use"),
                    preparation_note=p.get("preparation_note"),
                    contraindications=contra,
                    drug_interactions=inter,
                    side_effects=[str(x) for x in row.get("side_effects", []) if x],
                    warnings=["Hentikan penggunaan bila muncul reaksi yang tidak diinginkan."],
                    sources=sources,
                )
            )
        status = "completed" if candidates else "no_fully_verified_candidate"
        limitations = (
            []
            if candidates
            else ["Knowledge graph belum memiliki kandidat aman yang terverifikasi untuk keluhan tersebut."]
        )
        response = HerbalRecommendationResponse(
            status=status,
            request_id=request_id,
            recommendations=candidates,
            options=candidates,
            excluded_candidates=excluded,
            limitations=limitations,
            metadata={"knowledge_graph_checked": True, "candidate_count": len(candidates)},
        )
        if self.allow_mock:
            self._history.setdefault(user_id, []).append(
                {
                    "id": request_id,
                    "user_id": user_id,
                    "input": payload.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
        else:
            rows = await self.db.insert(
                "recommendation_sessions",
                {
                    "user_id": user_id,
                    "input": payload.model_dump(mode="json"),
                    "status": status,
                    "red_flags": red,
                    "limitations": limitations,
                },
            )
            session_id = rows[0]["id"]
            for candidate in candidates:
                await self.db.insert(
                    "recommendation_results",
                    {
                        "session_id": session_id,
                        "plant_id": candidate.plant_id,
                        "local_name": candidate.local_name,
                        "scientific_name": candidate.scientific_name,
                        "relevance_score": candidate.relevance_score,
                        "result": candidate.model_dump(mode="json"),
                    },
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
            {
                "select": "*,recommendation_results(*)",
                "id": f"eq.{session_id}",
                "user_id": f"eq.{user_id}",
                "limit": "1",
            },
        )
        if not rows:
            raise NotFoundError("Riwayat rekomendasi tidak ditemukan.")
        return rows[0]

    async def delete(self, user_id: str, session_id: str) -> None:
        await self.get(user_id, session_id)
        if self.allow_mock:
            self._history[user_id] = [x for x in self._history.get(user_id, []) if x["id"] != session_id]
        else:
            await self.db.delete(
                "recommendation_sessions", {"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"}
            )
