import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_services
from app.main import app
from app.graph.repositories import KnowledgeGraphRepository
from app.logic.recommendation_orchestrator import RecommendationOrchestrator
from app.models.auth import CurrentUser
from app.models.recommendation import HerbalRecommendationRequest
from app.services.recommendation.enrichment_mapper import map_enrichment_row


class FakeDB:
    async def insert(self, *args, **kwargs):
        return [{"id": "s1"}]


class LightRepo:
    def __init__(self):
        self.light_called = False
        self.detail_called = False

    async def recommend_herbs_light(self, terms, limit=8):
        self.light_called = True
        return [
            {
                "herb_id": "h1",
                "local_name": "Kencur",
                "scientific_name": "Kaempferia galanga",
                "matched_symptoms": ["batuk"],
                "active_compounds": ["ethyl cinnamate"],
                "safety_status": "unknown",
                "score": 0.8,
            }
        ]

    async def recommend_herbs_by_symptoms(self, terms, limit=8):
        raise AssertionError("full recommendation query should not be used")

    async def recommend_herbs_legacy(self, terms, limit=8):
        return []

    async def get_herb_detail_core(self, herb_id):
        self.detail_called = True
        return map_enrichment_row({"traditional_uses": [{"id": "tu1", "title": "Batuk"}]})


@pytest.mark.asyncio
async def test_analyze_uses_light_recommendation_query():
    repo = LightRepo()
    orch = RecommendationOrchestrator(repo, FakeDB(), allow_mock=True)
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk", symptoms=["batuk"]), "r1")
    assert repo.light_called is True
    assert res.recommendations


@pytest.mark.asyncio
async def test_analyze_does_not_load_full_enrichment_when_lazy_detail_enabled():
    repo = LightRepo()
    orch = RecommendationOrchestrator(repo, FakeDB(), allow_mock=True)
    orch.settings.herbal_recommendation_lazy_detail = True
    await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk", symptoms=["batuk"]), "r1")
    assert repo.detail_called is False


class TimeoutRepo(LightRepo):
    async def recommend_herbs_light(self, terms, limit=8):
        self.light_called = True
        return []


@pytest.mark.asyncio
async def test_analyze_returns_completed_with_warning_when_neo4j_timeout():
    orch = RecommendationOrchestrator(TimeoutRepo(), FakeDB(), allow_mock=True)
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk", symptoms=["batuk"]), "r1")
    assert res.status == "completed"
    assert res.recommendations == []
    assert res.warnings


class FailingDetailRepo(LightRepo):
    async def get_herb_detail_core(self, herb_id):
        raise TimeoutError("timed out")


@pytest.mark.asyncio
async def test_analyze_does_not_raise_500_when_neo4j_detail_fails():
    orch = RecommendationOrchestrator(FailingDetailRepo(), FakeDB(), allow_mock=True)
    orch.settings.herbal_recommendation_lazy_detail = False
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk", symptoms=["batuk"]), "r1")
    assert res.status == "completed"
    assert res.recommendations


class FakeClient:
    def __init__(self, rows=None, fail=False):
        self.rows = rows or []
        self.fail = fail
        self.calls = []

    async def read(self, query, params, timeout_seconds=None, max_retries=None):
        self.calls.append((query, params, timeout_seconds, max_retries))
        if self.fail:
            raise TimeoutError("timed out")
        return self.rows


@pytest.mark.asyncio
async def test_get_herb_detail_endpoint_returns_empty_detail_when_neo4j_timeout():
    async def fake_user():
        return CurrentUser(id="u1", email="u@example.test")

    class ServicesObj:
        recommendation_orchestrator = RecommendationOrchestrator(
            KnowledgeGraphRepository(FakeClient(fail=True)), FakeDB(), allow_mock=True
        )

    app.dependency_overrides[get_current_user] = fake_user
    app.dependency_overrides[get_services] = lambda: ServicesObj()
    try:
        client = TestClient(app)
        response = client.get("/api/herbal-recommendations/herbs/h1/detail")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["detail"]["traditional_uses"] == []


@pytest.mark.asyncio
async def test_get_herb_detail_core_maps_traditional_uses():
    repo = KnowledgeGraphRepository(FakeClient([{"traditional_uses": [{"id": "tu1", "title": "Batuk"}]}]))
    assert (await repo.get_herb_detail_core("h1"))["traditional_uses"][0]["title"] == "Batuk"


@pytest.mark.asyncio
async def test_get_herb_detail_core_maps_preparation_methods():
    repo = KnowledgeGraphRepository(FakeClient([{"preparation_methods": [{"id": "p1", "title": "Seduh"}]}]))
    assert (await repo.get_herb_detail_core("h1"))["preparation_methods"][0]["title"] == "Seduh"


@pytest.mark.asyncio
async def test_get_herb_detail_core_maps_usage_guidelines():
    repo = KnowledgeGraphRepository(FakeClient([{"usage_guidelines": [{"id": "g1", "title": "Pakai wajar"}]}]))
    assert (await repo.get_herb_detail_core("h1"))["usage_guidelines"][0]["title"] == "Pakai wajar"


@pytest.mark.asyncio
async def test_get_herb_detail_core_maps_safety_warnings():
    repo = KnowledgeGraphRepository(FakeClient([{"safety_warnings": [{"id": "w1", "title": "Hati-hati"}]}]))
    assert (await repo.get_herb_detail_core("h1"))["safety_warnings"][0]["title"] == "Hati-hati"


@pytest.mark.asyncio
async def test_recommendation_response_backward_compatible():
    orch = RecommendationOrchestrator(LightRepo(), FakeDB(), allow_mock=True)
    res = await orch.analyze("u1", HerbalRecommendationRequest(complaint="batuk", symptoms=["batuk"]), "r1")
    body = res.model_dump()
    assert "recommendations" in body
    assert "options" in body
    assert body["options"] == body["recommendations"]


def test_no_chat_endpoint_changed():
    from app.api.v1.chats import router as chat_router

    paths = {route.path for route in chat_router.routes if hasattr(route, "path")}
    assert "/api/chat/list" in paths
    assert "/api/v1/chats" in paths
