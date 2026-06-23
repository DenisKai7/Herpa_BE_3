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
from app.services.quiz.quiz_engine import (
    calculate_topic_progress,
    calculate_user_level,
    extract_accepted_answers,
    format_correct_answer,
    is_answer_correct,
    is_level_unlocked,
    normalize_answer,
)
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
    if qtype in {"multiple_choice"}:
        return "A"
    if qtype in {"case_based", "case_study"}:
        return "kimia unsur golongan orbital atom"
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


def _correct_option_id(question: dict, raw_question: dict):
    answer = _correct_answer(raw_question)
    for option in question.get("options", []):
        if option.get("id") == answer or option.get("text") == answer:
            return option["id"]
    for option in question.get("options", []):
        if option.get("label") == answer:
            return option["id"]
    return question["options"][0]["id"]


def _complete_session(client: TestClient, service: QuizService, topic_id: str = "struktur-atom", level_number: int = 1):
    session = client.post("/api/quiz/sessions", json={"topic_id": topic_id, "level_number": level_number}).json()
    raw_questions = {q["id"]: q for q in service.repository._sessions[session["id"]]["questions"]}
    for question in session["questions"]:
        raw_question = raw_questions[question["id"]]
        payload = {"question_id": question["id"], "answer": _correct_answer(raw_question)}
        if question["question_type"] in {"multiple_choice"}:
            payload = {
                "question_id": question["id"],
                "selected_option_id": _correct_option_id(question, raw_question),
                "elapsed_ms": 100,
            }
        elif question["question_type"] in {"case_based", "case_study"}:
            payload = {
                "question_id": question["id"],
                "answer_text": "kimia unsur golongan orbital atom",
                "elapsed_ms": 100,
            }
        client.post(f"/api/quiz/sessions/{session['id']}/answer", json=payload)
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
    assert len(topics) == 17
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


def test_level_5_is_case_study(quiz_client):
    client, _ = quiz_client
    levels = client.get("/api/quiz/topics").json()["topics"][0]["levels"]
    assert levels[4]["quiz_type"] == "case_study"


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


def test_matching_question_returns_render_items(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 2}).json()
    question = session["questions"][0]
    assert "correct_answer" not in question
    assert question["left_items"]
    assert question["right_items"]
    assert question["matching_pairs"]["left_items"] == question["left_items"]
    assert question["matching_pairs"]["right_items"] == question["right_items"]


def test_submit_matching_answer(quiz_client):
    client, service = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 2}).json()
    question = session["questions"][0]
    db_question = service.repository._sessions[session["id"]]["questions"][0]
    correct_ans = db_question["correct_answer"]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "matching_answer": correct_ans},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True
    saved = service.repository._answers[session["id"]][0]["answer"]
    assert saved["question_type"] == "matching"
    assert saved["matching_answer"] == {str(k): str(v) for k, v in correct_ans.items()}


def test_submit_incomplete_matching_answer_returns_400(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 2}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "matching_answer": {}},
    )
    assert response.status_code == 400
    assert response.json()["detail"]["message"] == "Jawaban mencocokkan belum lengkap."


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


def test_normalize_answer():
    from app.services.quiz.quiz_engine import normalize_answer
    assert normalize_answer("  Alkana  ") == "alkana"
    assert normalize_answer("Alkana   Murni") == "alkana murni"
    assert normalize_answer("alkana‐tertiary–secondary—normal−isomer") == "alkana-tertiary-secondary-normal-isomer"
    assert normalize_answer(None) == ""


def test_extract_accepted_answers():
    from app.services.quiz.quiz_engine import extract_accepted_answers
    # String
    assert extract_accepted_answers("alkana") == ["alkana"]
    # List
    assert extract_accepted_answers(["alkana", "alkena", None]) == ["alkana", "alkena"]
    # Dict shapes
    assert extract_accepted_answers({"accepted_answers": ["alkana", "alkena"]}) == ["alkana", "alkena"]
    assert extract_accepted_answers({"keywords": ["alkana", "alkena"]}) == ["alkana", "alkena"]
    assert extract_accepted_answers({"answers": ["alkana", "alkena"]}) == ["alkana", "alkena"]
    assert extract_accepted_answers({"answer": "alkana"}) == ["alkana"]
    assert extract_accepted_answers({"value": "alkana"}) == ["alkana"]
    assert extract_accepted_answers({"correct": "alkana"}) == ["alkana"]
    assert extract_accepted_answers({"text": "alkana"}) == ["alkana"]
    assert extract_accepted_answers({"label": "alkana"}) == ["alkana"]
    # External accepted_answers
    assert extract_accepted_answers("alkana", ["alkena"]) == ["alkana", "alkena"]


def test_submit_short_answer_variations(quiz_client):
    client, service = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 4}).json()
    question = session["questions"][0]
    db_question = service.repository._sessions[session["id"]]["questions"][0]
    correct_ans = format_correct_answer(db_question["correct_answer"])

    # Test lowercase
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer_text": correct_ans.lower()},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is True
    assert data["is_correct"] is True
    assert data["question_type"] == "short_answer"
    assert data["answer_text"] == correct_ans.lower()
    assert data["formatted_correct_answer"] == correct_ans

    # Test uppercase/capitalized
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer_text": correct_ans.upper()},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True

    # Test spacing variation
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer_text": f"   {correct_ans}   "},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True


def test_submit_short_answer_incorrect(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 4}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer_text": "salah-total-bukan-ini"},
    )
    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert response.json()["is_correct"] is False


def test_submit_short_answer_empty_returns_400(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 4}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "answer_text": "   "},
    )
    assert response.status_code == 400
    assert "Jawaban singkat tidak boleh kosong" in response.json()["detail"]["message"]


def test_all_17_topics_level_4(quiz_client):
    client, service = quiz_client
    topics = client.get("/api/quiz/topics").json()["topics"]
    assert len(topics) == 17
    for topic in topics:
        session = client.post("/api/quiz/sessions", json={"topic_id": topic["id"], "level_number": 4}).json()
        assert len(session["questions"]) == 10
        raw_questions = {q["id"]: q for q in service.repository._sessions[session["id"]]["questions"]}
        for question in session["questions"]:
            assert question["question_type"] == "short_answer"
            raw_question = raw_questions[question["id"]]
            correct_ans = format_correct_answer(raw_question["correct_answer"])
            response = client.post(
                f"/api/quiz/sessions/{session['id']}/answer",
                json={"question_id": question["id"], "answer_text": correct_ans},
            ).json()
            assert response["correct"] is True
            assert response["is_correct"] is True
            assert response["formatted_correct_answer"] == correct_ans


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


def test_submit_answer_accepts_selected_option_payload(quiz_client):
    client, service = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    raw_question = service.repository._sessions[session["id"]]["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={
            "question_id": question["id"],
            "selected_option_id": _correct_option_id(question, raw_question),
            "elapsed_ms": 321,
        },
    )
    assert response.status_code == 200
    assert response.json()["correct"] is True
    assert service.repository._answers[session["id"]][0]["duration_ms"] == 321


def test_submit_answer_invalid_attempt_returns_404(quiz_client):
    client, _ = quiz_client
    response = client.post(
        "/api/quiz/sessions/missing/answer",
        json={"question_id": "q", "selected_option_id": "o", "elapsed_ms": 0},
    )
    assert response.status_code == 404


def test_submit_answer_invalid_question_returns_404(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": "missing", "selected_option_id": "o", "elapsed_ms": 0},
    )
    assert response.status_code == 404


def test_submit_answer_invalid_option_returns_404(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "selected_option_id": "missing", "elapsed_ms": 0},
    )
    assert response.status_code == 404


def test_submit_answer_completed_attempt_returns_400(quiz_client):
    client, service = quiz_client
    session = _complete_session(client, service, level_number=1)
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={"question_id": question["id"], "selected_option_id": question["options"][0]["id"], "elapsed_ms": 0},
    )
    assert response.status_code == 400


def test_completion_does_not_double_xp(quiz_client):
    client, service = quiz_client
    session = _complete_session(client, service, level_number=1)
    assert client.get("/api/quiz/progress").json()["total_xp"] == 120
    client.post(f"/api/quiz/sessions/{session['id']}/complete")
    assert client.get("/api/quiz/progress").json()["total_xp"] == 120


def test_create_session_reuses_active_attempt(quiz_client):
    client, _ = quiz_client
    first = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    second = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    assert second["id"] == first["id"]


def test_multiple_choice_options_are_shuffled_but_stable(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    fetched = client.get(f"/api/quiz/sessions/{session['id']}").json()
    assert [o["id"] for o in fetched["questions"][0]["options"]] == [o["id"] for o in session["questions"][0]["options"]]
    labels = [option["label"] for option in session["questions"][0]["options"]]
    assert labels == ["A", "B", "C", "D"]


def test_dashboard_returns_progress_topics_and_active_sessions(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    response = client.get("/api/quiz/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "progress" in data
    assert len(data["topics"]) == 17
    assert any(item["session_id"] == session["id"] and item["status"] == "active" for item in data["active_sessions"])


def test_history_includes_active_continue_without_empty_duplicate_after_completion(quiz_client):
    client, service = quiz_client
    active = client.post("/api/quiz/sessions", json={"topic_id": "struktur-atom", "level_number": 1}).json()
    rows = client.get("/api/quiz/history").json()["history"]
    assert any(row["session_id"] == active["id"] and row["status"] == "active" for row in rows)
    completed = _complete_session(client, service, level_number=1)
    rows = client.get("/api/quiz/history").json()["history"]
    assert any(row["session_id"] == completed["id"] and row["status"] == "completed" for row in rows)
    assert not any(row["session_id"] == active["id"] and row["status"] == "active" for row in rows)


def test_submit_case_study_answer(quiz_client):
    client, service = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "tabel-periodik", "level_number": 5}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={
            "question_id": question["id"],
            "answer_text": "Senyawa ini memiliki elektron valensi yang stabil karena termasuk gas mulia.",
            "elapsed_ms": 500,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is True
    assert data["is_correct"] is True
    assert "elektron valensi" in data["matched_keywords"]
    assert "gas mulia" in data["matched_keywords"]


def test_submit_case_study_answer_incorrect(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "tabel-periodik", "level_number": 5}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={
            "question_id": question["id"],
            "answer_text": "Saya tidak tahu konsep apa ini sama sekali.",
            "elapsed_ms": 500,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["correct"] is False
    assert data["is_correct"] is False


def test_submit_case_study_too_short(quiz_client):
    client, _ = quiz_client
    session = client.post("/api/quiz/sessions", json={"topic_id": "tabel-periodik", "level_number": 5}).json()
    question = session["questions"][0]
    response = client.post(
        f"/api/quiz/sessions/{session['id']}/answer",
        json={
            "question_id": question["id"],
            "answer_text": "Pendek",
            "elapsed_ms": 500,
        },
    )
    assert response.status_code == 400
    assert "Jawaban studi kasus terlalu pendek" in response.json()["detail"]


def test_all_17_topics_level_5(quiz_client):
    client, service = quiz_client
    topics = client.get("/api/quiz/topics").json()["topics"]
    assert len(topics) == 17
    for topic in topics:
        session = client.post("/api/quiz/sessions", json={"topic_id": topic["id"], "level_number": 5}).json()
        assert len(session["questions"]) == 10
        raw_questions = {q["id"]: q for q in service.repository._sessions[session["id"]]["questions"]}
        for question in session["questions"]:
            assert question["question_type"] == "case_study"
            raw_question = raw_questions[question["id"]]
            kws = raw_question["correct_answer"]["required_keywords"]
            ans_text = " ".join(kws)
            response = client.post(
                f"/api/quiz/sessions/{session['id']}/answer",
                json={"question_id": question["id"], "answer_text": ans_text},
            ).json()
            assert response["correct"] is True
            assert response["is_correct"] is True
