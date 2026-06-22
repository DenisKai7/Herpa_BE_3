from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_services
from app.core.config import Settings
from app.main import app
from app.models.auth import CurrentUser
from app.services.supabase.client import SupabaseClient
from app.services.supabase.profile_service import ProfileService
from app.services.supabase.quiz_service import QuizService


@pytest.fixture()
def quiz_client():
    settings = Settings(app_env="test", allow_mock_services=True)
    supabase = SupabaseClient(settings)
    quiz_service = QuizService(supabase)
    profile_service = ProfileService(supabase)
    services = SimpleNamespace(settings=settings, profiles=profile_service, quiz_service=quiz_service)

    async def user_one():
        return CurrentUser(id="11111111-1111-1111-1111-111111111111", email="u1@example.test")

    app.dependency_overrides[get_current_user] = user_one
    app.dependency_overrides[get_services] = lambda: services
    try:
        yield TestClient(app), quiz_service
    finally:
        app.dependency_overrides.clear()


def _answer_for(question: dict):
    qtype = question["question_type"]
    if qtype in {"multiple_choice", "case_based"}:
        return "A"
    if qtype == "matching":
        return question["matching_pairs"]
    if qtype == "true_false":
        return True
    if qtype == "short_answer":
        return "kimia"
    return "A"


def _correct_answer(raw_question: dict):
    answer = raw_question["correct_answer"]
    if isinstance(answer, dict) and "answer" in answer:
        return answer["answer"]
    return answer


def _complete_session(client: TestClient, service: QuizService, topic_id: str = "struktur-atom", level_number: int = 1):
    session = client.post("/api/quiz/sessions", json={"topic_id": topic_id, "level_number": level_number}).json()
    raw_questions = {q["id"]: q for q in service.repository._sessions[session["id"]]["questions"]}
    for question in session["questions"]:
        answer = _correct_answer(raw_questions[question["id"]])
        client.post(
            f"/api/quiz/sessions/{session['id']}/answer",
            json={"question_id": question["id"], "answer": answer},
        )
    return session


def test_quiz_progress_returns_200(quiz_client):
    client, _ = quiz_client
    response = client.get("/api/quiz/progress")
    assert response.status_code == 200
    data = response.json()
    assert data["total_xp"] == 0
    assert data["level"] == 1
    assert data["topic_progress"] == []


def test_quiz_topics_returns_200(quiz_client):
    client, _ = quiz_client
    response = client.get("/api/quiz/topics")
    assert response.status_code == 200
    data = response.json()
    topics = data["topics"]
    assert len(topics) == 16
    assert topics[0]["title"] == "Struktur Atom"


def test_each_topic_has_5_levels(quiz_client):
    client, _ = quiz_client
    topics = client.get("/api/quiz/topics").json()["topics"]
    assert all(len(topic["levels"]) == 5 for topic in topics)


def test_level_1_is_multiple_choice(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[0]["quiz_type"] == "multiple_choice"


def test_level_2_is_matching(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[1]["quiz_type"] == "matching"


def test_level_3_is_true_false(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[2]["quiz_type"] == "true_false"


def test_level_4_is_short_answer(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[3]["quiz_type"] == "short_answer"


def test_level_5_is_case_based(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[4]["quiz_type"] == "case_based"


def test_start_session_returns_5_questions(quiz_client):
    client, _ = quiz_client
    response = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["topic_id"] == "struktur-atom"
    assert data["level_id"] == "struktur-atom-level-1"
    assert data["total_questions"] == 10
    assert len(data["questions"]) == 10
    assert data["questions"][0]["question_type"] == "multiple_choice"
    assert "correct_answer" not in data["questions"][0]


def test_answer_endpoint_exists(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer": "A"},
    )
    assert response.status_code != 404


def test_submit_answer_not_404(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer": "A"},
    )
    assert response.status_code == 200


def test_submit_answer_saves_answer(quiz_client):
    client, service = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer": "A"},
    )
    assert response.status_code == 200
    assert service.repository._answers[session["id"]][0]["question_id"] == question["id"]
    assert "correct_answer" in service.repository._answers[session["id"]][0]


def test_submit_multiple_choice_answer_feedback(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer": "A"},
    )
    data = response.json()
    assert data["correct"] is True
    assert data["explanation"]
    assert data["score_delta"] == 10


def test_submit_matching_answer(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 2}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer": question["matching_pairs"]},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True


def test_complete_session_updates_xp(quiz_client):
    client, service = quiz_client
    _complete_session(client, service, level_number=1)
    progress = client.get("/api/quiz/progress").json()
    assert progress["total_xp"] == 120  # 10 correct * 10 + pass bonus 20
    assert progress["level"] == 2


def test_complete_session_updates_topic_progress(quiz_client):
    client, service = quiz_client
    _complete_session(client, service, level_number=1)
    progress = client.get("/api/quiz/progress").json()
    topic_progress = next(row for row in progress["topic_progress"] if row["topic_id"] == "struktur-atom")
    assert topic_progress["highest_level_completed"] == 1
    assert topic_progress["topic_progress"] == 20
    topics = client.get("/api/quiz/topics").json()["topics"]
    topic = next(row for row in topics if row["id"] == "struktur-atom")
    assert topic["levels"][1]["is_locked"] is False


def test_history_returns_completed_sessions(quiz_client):
    client, service = quiz_client
    session = _complete_session(client, service, level_number=1)
    history = client.get("/api/quiz/history")
    assert history.status_code == 200
    rows = history.json()["history"]
    assert any(row["session_id"] == session["id"] for row in rows)
    assert rows[0]["topic_title"]
    assert rows[0]["passed"] is True


def test_summary_returns_explanations(quiz_client):
    client, service = quiz_client
    session = _complete_session(client, service, level_number=1)
    summary = client.get(f"/api/quiz/sessions/{session['id']}/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["session_id"] == session["id"]
    assert data["score"] == 100
    assert data["xp_earned"] == 120
    assert data["passed"] is True
    assert data["next_level_unlocked"] is True
    assert data["next_level_number"] == 2
    assert len(data["explanations"]) == 10
    assert data["explanations"][0]["explanation"]


def test_optional_topic_detail_endpoint(quiz_client):
    client, _ = quiz_client
    response = client.get("/api/quiz/topics/struktur-atom")
    assert response.status_code == 200
    assert response.json()["id"] == "struktur-atom"


def test_optional_topic_levels_endpoint(quiz_client):
    client, _ = quiz_client
    response = client.get("/api/quiz/topics/struktur-atom/levels")
    assert response.status_code == 200
    assert len(response.json()) == 5


def test_optional_topic_level_detail_endpoint(quiz_client):
    client, _ = quiz_client
    response = client.get("/api/quiz/topics/struktur-atom/levels/1")
    assert response.status_code == 200
    data = response.json()
    assert data["level_number"] == 1
    assert len(data["questions"]) == 10
    assert "correct_answer" not in data["questions"][0]


def test_optional_complete_endpoint_before_done(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    response = client.post(f"/api/quiz/sessions/{session['id']}/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is False


def test_seed_invariants():
    from app.services.quiz.quiz_seed import QUIZ_SEED_TOPICS

    assert len(QUIZ_SEED_TOPICS) == 16
    for topic in QUIZ_SEED_TOPICS:
        assert len(topic["levels"]) == 5
        for level in topic["levels"]:
            questions = [q for q in topic["questions"] if q["level_id"] == level["id"]]
            assert len(questions) >= 10


def test_admin_login_role_admin(quiz_client):
    client, _ = quiz_client
    response = client.post("/api/auth/login", json={"email": "admin@admin.com", "password": "Password123"})
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "admin"


def test_user_cannot_access_other_user_session(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()

    async def user_two():
        return CurrentUser(id="22222222-2222-2222-2222-222222222222", email="u2@example.test")

    app.dependency_overrides[get_current_user] = user_two
    response = client.get(f"/api/quiz/sessions/{session['id']}")
    assert response.status_code == 404
