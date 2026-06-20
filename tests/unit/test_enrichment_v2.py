import pytest

from app.graph.query_templates import HERBAL_RECOMMENDATION_BY_SYMPTOMS
from app.graph.repositories import KnowledgeGraphRepository
from app.logic.recommendation_orchestrator import RecommendationOrchestrator
from app.models.recommendation import HerbEnrichmentDetail, HerbalCandidate, HerbalRecommendationRequest
from app.services.recommendation.enrichment_mapper import (
    filter_by_persona,
    map_enrichment_row,
)


def test_enrichment_schema_models():
    item = HerbalCandidate(plant_id="h1", local_name="Kencur")
    assert isinstance(item.enrichment, HerbEnrichmentDetail)
    assert item.traditional_uses == []
    assert item.preparation_methods == []
    assert item.usage_guidelines == []
    assert item.safety_warnings == []


def test_map_enrichment_row_filters_empty_optional_match():
    mapped = map_enrichment_row({"traditional_uses": [{"id": None, "title": None}], "plant_parts": [{}]})
    assert mapped["traditional_uses"] == []
    assert mapped["plant_parts"] == []


def test_map_enrichment_row_dedupes_sources():
    mapped = map_enrichment_row(
        {
            "traditional_uses": [
                {
                    "id": "tu1",
                    "title": "Batuk",
                    "sources": [
                        {"source_id": "s1", "title": "Materia"},
                        {"source_id": "s1", "title": "Materia"},
                    ],
                }
            ]
        }
    )
    assert len(mapped["traditional_uses"][0]["sources"]) == 1


class FakeClient:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def read(self, query, params, **kwargs):
        self.calls.append((query, params))
        return self.rows


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_returns_empty_lists_when_no_data():
    repo = KnowledgeGraphRepository(FakeClient([]))
    data = await repo.get_herb_enrichment_detail("missing")
    assert data["traditional_uses"] == []
    assert data["claims"] == []


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_traditional_uses():
    repo = KnowledgeGraphRepository(FakeClient([{"traditional_uses": [{"id": "tu1", "title": "Batuk"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["traditional_uses"][0]["title"] == "Batuk"


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_preparation_methods():
    repo = KnowledgeGraphRepository(FakeClient([{"preparation_methods": [{"id": "p1", "title": "Seduhan", "steps": ["Cuci"]}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["preparation_methods"][0]["steps"] == ["Cuci"]


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_usage_guidelines():
    repo = KnowledgeGraphRepository(FakeClient([{"usage_guidelines": [{"id": "g1", "title": "Edukasi"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["usage_guidelines"][0]["title"] == "Edukasi"


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_safety_warnings():
    repo = KnowledgeGraphRepository(FakeClient([{"safety_warnings": [{"id": "w1", "title": "Hati-hati"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["safety_warnings"][0]["severity"] == "caution"


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_claims_and_evidence():
    repo = KnowledgeGraphRepository(FakeClient([{"claims": [{"claim_id": "c1", "claim_text": "Membantu", "evidence_level": "review"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["claims"][0]["evidence_level"] == "review"


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_drug_interactions():
    repo = KnowledgeGraphRepository(FakeClient([{"drug_interactions": [{"id": "i1", "substance": "Warfarin"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["drug_interactions"][0]["substance"] == "Warfarin"


@pytest.mark.asyncio
async def test_get_herb_enrichment_detail_maps_contraindications():
    repo = KnowledgeGraphRepository(FakeClient([{"contraindications": [{"id": "k1", "condition": "Hamil"}]}]))
    data = await repo.get_herb_enrichment_detail("h1")
    assert data["contraindications"][0]["condition"] == "Hamil"


@pytest.mark.asyncio
async def test_recommendation_by_symptoms_uses_symptom_aliases():
    client = FakeClient([{"herb_id": "h1"}])
    repo = KnowledgeGraphRepository(client)
    rows = await repo.recommend_herbs_by_symptoms(["batuk berdahak"], 3)
    assert rows == [{"herb_id": "h1"}]
    assert client.calls[0][0] == HERBAL_RECOMMENDATION_BY_SYMPTOMS
    assert client.calls[0][1]["expanded_terms"] == ["batuk berdahak"]


class FakeRepo:
    async def recommend_herbs_light(self, terms, limit=8):
        return [{"herb_id": "h1", "local_name": "Kencur", "scientific_name": "Kaempferia galanga", "matched_symptoms": ["batuk"], "active_compounds": ["ethyl cinnamate"], "score": 0.8}]

    async def recommend_herbs_by_symptoms(self, expanded_terms, limit=8):
        return [{"herb_id": "h1", "local_name": "Kencur", "scientific_name": "Kaempferia galanga", "matched_symptoms": ["batuk"], "active_compounds": ["ethyl cinnamate"], "score": 0.8}]

    async def recommend_herbs_legacy(self, symptoms, limit=8):
        return []

    async def get_herb_enrichment_detail(self, herb_id=None, canonical_name=None, common_name=None):
        return map_enrichment_row({"traditional_uses": [{"id": "tu1", "title": "Batuk"}], "clinical_guidelines": [{"id": "cg1", "therapeutic_dose_text": "detail klinis", "visible_to": ["tenaga_medis"]}]})

    async def get_herb_detail_core(self, herb_id):
        return await self.get_herb_enrichment_detail(herb_id=herb_id)


class FakeDB:
    async def insert(self, *args, **kwargs):
        return [{"id": "s1"}]


@pytest.mark.asyncio
async def test_recommendation_item_contains_enrichment_fields():
    orch = RecommendationOrchestrator(FakeRepo(), FakeDB(), allow_mock=True)
    orch.settings.herbal_recommendation_lazy_detail = False
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk ringan", symptoms=["batuk"], persona="umum"), "r1")
    assert res.recommendations[0].traditional_uses[0].title == "Batuk"


@pytest.mark.asyncio
async def test_recommendation_response_json_safe_with_full_enrichment():
    orch = RecommendationOrchestrator(FakeRepo(), FakeDB(), allow_mock=True)
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk ringan", symptoms=["batuk"]), "r1")
    assert "NaN" not in res.model_dump_json()


def test_persona_filter_hides_clinical_detail_for_umum():
    data = {"clinical_guidelines": [{"id": "c1", "therapeutic_dose_text": "3x sehari", "visible_to": ["umum"]}]}
    filtered = filter_by_persona(data, "umum")
    assert filtered["clinical_guidelines"][0]["therapeutic_dose_text"] is None


def test_persona_filter_shows_clinical_detail_for_tenaga_medis():
    data = {"clinical_guidelines": [{"id": "c1", "therapeutic_dose_text": "3x sehari", "visible_to": ["tenaga_medis"]}]}
    filtered = filter_by_persona(data, "tenaga_medis")
    assert filtered["clinical_guidelines"][0]["therapeutic_dose_text"] == "3x sehari"


def test_no_diagnosis_or_replace_medical_treatment_claim():
    item = HerbalCandidate(plant_id="h1", local_name="Kencur")
    text = item.model_dump_json().lower()
    assert "diagnosis" not in text
    assert "mengganti obat" not in text
