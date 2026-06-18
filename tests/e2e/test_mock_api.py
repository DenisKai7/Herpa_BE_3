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
