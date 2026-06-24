from fastapi.testclient import TestClient
from app.main import app


def test_mock_user_flow():
    with TestClient(app) as client:
        login = client.post("/api/auth/login", json={"email": "user@example.com", "password": "password123"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['token']}"}
        created = client.post("/api/v1/chats", json={"title": "Tes"}, headers=headers)
        assert created.status_code == 200
        chat_id = created.json()["id"]
        reply = client.post(
            "/api/chat/message",
            json={"chat_id": chat_id, "message": "Jelaskan manfaat jahe", "ai_mode": "umum"},
            headers=headers,
        )
        assert reply.status_code == 200
        assert reply.json()["chat_id"] == chat_id
        recommendation = client.post(
            "/api/herbal-recommendations/analyze",
            json={"symptoms": ["mual"], "severity": "ringan"},
            headers=headers,
        )
        assert recommendation.status_code == 200
        assert recommendation.json()["recommendations"]
        quiz = client.post(
            "/api/v1/quiz/attempts", json={"level_id": "periodic-1", "question_count": 5}, headers=headers
        )
        assert quiz.status_code == 200


def test_admin_is_protected():
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer dev-user"}
        response = client.get("/api/admin/analytics", headers=headers)
        assert response.status_code == 403


def test_new_admin_endpoints():
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer dev-admin"}

        # Test GET /api/admin/health
        health = client.get("/api/admin/health", headers=headers)
        assert health.status_code == 200
        assert health.json()["overall"] in ("ok", "degraded")
        assert "supabase" in health.json()["services"]
        assert "neo4j" in health.json()["services"]
        assert "minio" in health.json()["services"]

        # Test GET /api/admin/model-usage
        model_usage = client.get("/api/admin/model-usage", headers=headers)
        assert model_usage.status_code == 200
        assert "entries" in model_usage.json()
        assert "summary" in model_usage.json()

        # Test GET /api/admin/graph-stats
        graph_stats = client.get("/api/admin/graph-stats", headers=headers)
        assert graph_stats.status_code == 200
        assert "herb_count" in graph_stats.json()
        assert "summary" in graph_stats.json()

        # Test GET /api/admin/recommendation-analytics
        rec_analytics = client.get("/api/admin/recommendation-analytics", headers=headers)
        assert rec_analytics.status_code == 200
        assert "total_sessions" in rec_analytics.json()
        assert "summary" in rec_analytics.json()

        # Test GET /api/admin/quiz-analytics
        quiz_analytics = client.get("/api/admin/quiz-analytics", headers=headers)
        assert quiz_analytics.status_code == 200
        assert "total_sessions" in quiz_analytics.json()
        assert "summary" in quiz_analytics.json()

        # Test GET /api/admin/storage-stats
        storage_stats = client.get("/api/admin/storage-stats", headers=headers)
        assert storage_stats.status_code == 200
        assert "buckets" in storage_stats.json()
        assert "summary" in storage_stats.json()

        # Test GET /api/admin/errors
        errors = client.get("/api/admin/errors", headers=headers)
        assert errors.status_code == 200
        assert "errors" in errors.json()
        assert "summary" in errors.json()

        # Test auth protection on new endpoints
        user_headers = {"Authorization": "Bearer dev-user"}
        endpoints = [
            "/api/admin/health",
            "/api/admin/model-usage",
            "/api/admin/graph-stats",
            "/api/admin/recommendation-analytics",
            "/api/admin/quiz-analytics",
            "/api/admin/storage-stats",
            "/api/admin/errors",
        ]
        for ep in endpoints:
            res = client.get(ep, headers=user_headers)
            assert res.status_code == 403

