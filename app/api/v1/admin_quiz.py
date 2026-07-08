import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser
from app.models.quiz_admin import (
    QuizLevelCreate,
    QuizLevelUpdate,
    QuizModuleCreate,
    QuizModuleUpdate,
    QuizQuestionCreate,
    QuizQuestionUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin Quiz"])


# ── Dashboard ──

@router.get("/api/admin/quiz/dashboard")
async def quiz_dashboard(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get quiz dashboard statistics."""
    return await services.admin_quiz.get_dashboard_stats()


# ── Modules ──

@router.get("/api/admin/quiz/modules")
async def list_modules(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    rows, total = await services.admin_quiz.list_modules(limit=limit, offset=offset, search=search)
    return {"modules": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/api/admin/quiz/modules", status_code=201)
async def create_module(
    payload: QuizModuleCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.create_module(payload.model_dump())
    await services.admin.audit(
        admin.id, "quiz.module.created", "quiz_modules", str(result.get("id")),
        None, {"title": payload.title}, request.state.request_id,
    )
    return result


@router.put("/api/admin/quiz/modules/{module_id}")
async def update_module(
    module_id: str,
    payload: QuizModuleUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.update_module(module_id, payload.model_dump(exclude_unset=True))
    await services.admin.audit(
        admin.id, "quiz.module.updated", "quiz_modules", module_id,
        None, payload.model_dump(exclude_unset=True), request.state.request_id,
    )
    return result


@router.delete("/api/admin/quiz/modules/{module_id}")
async def delete_module(
    module_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    ok = await services.admin_quiz.delete_module(module_id)
    await services.admin.audit(
        admin.id, "quiz.module.deleted", "quiz_modules", module_id,
        None, {"deleted": ok}, request.state.request_id,
    )
    return {"message": "Module berhasil dihapus." if ok else "Gagal menghapus module."}


# ── Levels ──

@router.get("/api/admin/quiz/levels")
async def list_levels(
    module_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    rows, total = await services.admin_quiz.list_levels(module_id=module_id, limit=limit, offset=offset)
    return {"levels": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/api/admin/quiz/levels", status_code=201)
async def create_level(
    payload: QuizLevelCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.create_level(payload.model_dump())
    await services.admin.audit(
        admin.id, "quiz.level.created", "quiz_levels", str(result.get("id")),
        None, {"title": payload.title}, request.state.request_id,
    )
    return result


@router.put("/api/admin/quiz/levels/{level_id}")
async def update_level(
    level_id: str,
    payload: QuizLevelUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.update_level(level_id, payload.model_dump(exclude_unset=True))
    await services.admin.audit(
        admin.id, "quiz.level.updated", "quiz_levels", level_id,
        None, payload.model_dump(exclude_unset=True), request.state.request_id,
    )
    return result


@router.delete("/api/admin/quiz/levels/{level_id}")
async def delete_level(
    level_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    ok = await services.admin_quiz.delete_level(level_id)
    await services.admin.audit(
        admin.id, "quiz.level.deleted", "quiz_levels", level_id,
        None, {"deleted": ok}, request.state.request_id,
    )
    return {"message": "Level berhasil dihapus." if ok else "Gagal menghapus level."}


# ── Questions ──

@router.get("/api/admin/quiz/questions")
async def list_questions(
    level_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    rows, total = await services.admin_quiz.list_questions(
        level_id=level_id, limit=limit, offset=offset, search=search,
    )
    return {"questions": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/api/admin/quiz/questions/{question_id}")
async def get_question(
    question_id: str,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    return await services.admin_quiz.get_question(question_id)


@router.post("/api/admin/quiz/questions", status_code=201)
async def create_question(
    payload: QuizQuestionCreate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.create_question(payload.model_dump())
    await services.admin.audit(
        admin.id, "quiz.question.created", "quiz_questions", str(result.get("id")),
        None, {"prompt": payload.prompt[:100]}, request.state.request_id,
    )
    return result


@router.put("/api/admin/quiz/questions/{question_id}")
async def update_question(
    question_id: str,
    payload: QuizQuestionUpdate,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    result = await services.admin_quiz.update_question(question_id, payload.model_dump(exclude_unset=True))
    await services.admin.audit(
        admin.id, "quiz.question.updated", "quiz_questions", question_id,
        None, payload.model_dump(exclude_unset=True), request.state.request_id,
    )
    return result


@router.delete("/api/admin/quiz/questions/{question_id}")
async def delete_question(
    question_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    ok = await services.admin_quiz.delete_question(question_id)
    await services.admin.audit(
        admin.id, "quiz.question.deleted", "quiz_questions", question_id,
        None, {"deleted": ok}, request.state.request_id,
    )
    return {"message": "Soal berhasil dihapus." if ok else "Gagal menghapus soal."}
