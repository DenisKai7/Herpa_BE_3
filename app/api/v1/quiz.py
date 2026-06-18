from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser
from app.models.quiz import QuizAnswerRequest, QuizAttemptCreate

router = APIRouter(prefix="/api/v1/quiz", tags=["Quiz"])


@router.get("/subjects")
async def subjects(services: Services = Depends(get_services)):
    return await services.quiz_service.subjects()


@router.get("/modules")
async def modules(subject_id: str | None = Query(default=None), services: Services = Depends(get_services)):
    return await services.quiz_service.modules(subject_id)


@router.get("/modules/{module_id}")
async def module(module_id: str, services: Services = Depends(get_services)):
    return await services.quiz_service.module(module_id)


@router.get("/levels/{level_id}")
async def level(level_id: str, services: Services = Depends(get_services)):
    return await services.quiz_service.level(level_id)


@router.post("/attempts")
async def start(
    payload: QuizAttemptCreate,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_orchestrator.start(user.id, payload.level_id, payload.question_count)


@router.get("/attempts/{attempt_id}")
async def get_attempt(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return await services.quiz_service.get_attempt(user.id, attempt_id)


@router.post("/attempts/{attempt_id}/answers")
async def answer(
    attempt_id: str,
    payload: QuizAnswerRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    return await services.quiz_orchestrator.answer(user.id, attempt_id, payload.model_dump())


@router.post("/attempts/{attempt_id}/complete")
async def complete(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return await services.quiz_orchestrator.complete(user.id, attempt_id)


@router.get("/history")
async def history(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.history(user.id)


@router.delete("/history/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_history(
    attempt_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> Response:
    await services.quiz_service.delete_history(user.id, attempt_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/progress")
async def progress(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.quiz_service.progress(user.id)
