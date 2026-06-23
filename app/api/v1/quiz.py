from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser
from app.models.quiz import QuizAnswerRequest, QuizAttemptCreate
from app.schemas.quiz import StartQuizSessionRequest, SubmitAnswerRequest

router = APIRouter(tags=["Quiz"])


@router.get("/api/v1/quiz/subjects")
async def subjects(services: Services = Depends(get_services)):
    return await services.quiz_service.subjects()


@router.get("/api/v1/quiz/modules")
async def modules(subject_id: str | None = Query(default=None), services: Services = Depends(get_services)):
    return await services.quiz_service.modules(subject_id)


@router.get("/api/v1/quiz/modules/{module_id}")
async def module(module_id: str, services: Services = Depends(get_services)):
    return await services.quiz_service.module(module_id)


@router.get("/api/v1/quiz/levels/{level_id}")
async def level(level_id: str, services: Services = Depends(get_services)):
    return await services.quiz_service.level(level_id)


@router.post("/api/v1/quiz/attempts")
async def start(
    payload: QuizAttemptCreate,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_orchestrator.start(user.id, payload.level_id, payload.question_count)


@router.get("/api/v1/quiz/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return await services.quiz_service.get_attempt(user.id, attempt_id)


@router.post("/api/v1/quiz/attempts/{attempt_id}/answers")
async def answer(
    attempt_id: str,
    payload: QuizAnswerRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_orchestrator.answer(user.id, attempt_id, payload.model_dump())


@router.post("/api/v1/quiz/attempts/{attempt_id}/complete")
async def complete(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return await services.quiz_orchestrator.complete(user.id, attempt_id)


@router.get("/api/v1/quiz/history")
async def history(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.history(user.id)


@router.delete("/api/v1/quiz/history/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> Response:
    await services.quiz_service.delete_history(user.id, attempt_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/v1/quiz/progress")
async def old_progress(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.progress(user.id)


# New frontend-facing quiz API. Additive, non-breaking.


@router.get("/api/quiz/progress")
async def quiz_progress(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.new_progress(user.id)


@router.get("/api/quiz/topics")
async def quiz_topics(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.topics(user.id)


@router.get("/api/quiz/dashboard")
async def quiz_dashboard(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    progress = await services.quiz_service.new_progress(user.id)
    topics = await services.quiz_service.topics(user.id)
    history = await services.quiz_service.new_history(user.id)
    active_sessions = [item for item in history.get("history", []) if item.get("status") == "active"]
    return {"progress": progress, "topics": topics.get("topics", []), "active_sessions": active_sessions}


@router.post("/api/quiz/sessions")
async def create_quiz_session(
    payload: StartQuizSessionRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    session = await services.quiz_service.create_session(user.id, payload.topic_id, payload.level_id, payload.level_number)
    questions = session.get("questions") or await services.quiz_service.repository.get_questions_for_level(
        session["level_id"], session["topic_id"]
    )
    public_questions = [services.quiz_service.repository._public_question(q) for q in questions]
    return {
        "id": session["id"],
        "attempt_id": session["id"],
        "topic_id": session["topic_id"],
        "level_id": session["level_id"],
        "status": session.get("status", "active"),
        "score": session.get("score", 0),
        "total_questions": session.get("total_questions", len(public_questions)),
        "current_question_index": session.get("current_question_index", 0),
        "questions": public_questions,
    }


@router.get("/api/quiz/sessions/{session_id}")
async def get_quiz_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    session = await services.quiz_service.get_session(user.id, session_id)
    questions = session.get("questions") or await services.quiz_service.repository.get_questions_for_level(
        session["level_id"], session["topic_id"]
    )
    answers = await services.quiz_service.repository._answers_for_session(session_id)
    answer_by_question = {str(answer["question_id"]): answer for answer in answers}
    public_questions = []
    for question in questions:
        item = services.quiz_service.repository._public_question(question)
        answer = answer_by_question.get(str(question["id"]))
        if answer:
            item["user_answer"] = answer.get("answer") or answer.get("user_answer")
        public_questions.append(item)
    return {
        "id": session["id"],
        "attempt_id": session["id"],
        "topic_id": session["topic_id"],
        "level_id": session["level_id"],
        "status": session.get("status", "active"),
        "score": session.get("score", 0),
        "total_questions": session.get("total_questions", len(questions)),
        "current_question_index": session.get("current_question_index", len(answers)),
        "questions": public_questions,
    }


@router.get("/api/quiz/topics/{topic_id}")
async def quiz_topic_detail(
    topic_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    topics = await services.quiz_service.topics(user.id)
    for topic in topics.get("topics", []):
        if topic["id"] == topic_id:
            return topic
    from app.core.exceptions import NotFoundError

    raise NotFoundError("Topik quiz tidak ditemukan.")


@router.get("/api/quiz/topics/{topic_id}/levels")
async def quiz_topic_levels(
    topic_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_service.repository.get_topic_levels(topic_id, user.id)


@router.get("/api/quiz/topics/{topic_id}/levels/{level_number}")
async def quiz_topic_level_detail(
    topic_id: str,
    level_number: int,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    levels = await services.quiz_service.repository.get_topic_levels(topic_id, user.id)
    for level in levels:
        if int(level["level_number"]) == int(level_number):
            questions = await services.quiz_service.repository.get_questions_for_level(level["id"], topic_id)
            return {
                **level,
                "questions": [services.quiz_service.repository._public_question(q) for q in questions[:10]],
            }
    from app.core.exceptions import NotFoundError

    raise NotFoundError("Level quiz tidak ditemukan.")


@router.post("/api/quiz/sessions/{attempt_id}/answer")
async def submit_quiz_answer(
    attempt_id: str,
    payload: SubmitAnswerRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_service.submit_session_answer(
        user.id,
        attempt_id,
        payload.question_id,
        payload.answer,
        payload.selected_option_id,
        payload.elapsed_ms,
    )


@router.post("/api/quiz/sessions/{session_id}/complete")
async def complete_quiz_session(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    completion = await services.quiz_service.repository.complete_session_if_done(user.id, session_id)
    return await services.quiz_service.session_summary(user.id, session_id) if completion["completed"] else completion


@router.get("/api/quiz/sessions/{session_id}/summary")
async def quiz_session_summary(
    session_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_service.session_summary(user.id, session_id)


@router.get("/api/quiz/history")
async def quiz_history(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.new_history(user.id)
