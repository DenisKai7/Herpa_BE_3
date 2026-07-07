import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.core.constants import AccountStatus, ApplicationRole
from app.core.exceptions import AppError, ForbiddenError
from app.models.admin import (
    AdminAnalytics,
    CreateUserRequest,
    DeleteUserRequest,
    UpdateUserRoleRequest,
    UpdateUserRequest,
    UpdateUserStatusRequest,
)
from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin"])


@router.get("/api/admin/analytics", response_model=AdminAnalytics)
@router.get("/api/v1/admin/overview", response_model=AdminAnalytics, include_in_schema=False)
async def analytics(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
) -> AdminAnalytics:
    return AdminAnalytics.model_validate(await services.admin.analytics())


@router.get("/api/admin/users")
@router.get("/api/v1/admin/users", include_in_schema=False)
async def users(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=100),
    role: ApplicationRole | None = Query(None),
    status: AccountStatus | None = Query(None),
    sort: Literal["full_name", "email", "created_at"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    rows, total = await services.admin.users(
        limit=limit,
        offset=offset,
        search=search,
        role=role.value if role else None,
        status=status.value if status else None,
        sort=sort,
        sort_dir=sort_dir,
    )
    return {"users": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/api/v1/admin/users/{user_id}")
async def user_detail(
    user_id: str, admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    return await services.admin.user(user_id)


@router.post("/api/admin/users/role")
async def role(
    payload: UpdateUserRoleRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    before = await services.admin.user(payload.user_id) if not services.settings.allow_mock_services else None
    profile = await services.profiles.set_role(payload.user_id, payload.role)
    await services.admin.audit(
        admin.id,
        "user.role.changed",
        "profile",
        payload.user_id,
        before,
        profile.model_dump(mode="json"),
        request.state.request_id,
    )
    return {
        "id": profile.id,
        "email": profile.email,
        "full_name": profile.full_name or "",
        "role": profile.application_role,
        "persona": profile.persona,
        "account_status": profile.account_status,
        "instansi": profile.instansi or "",
        "created_at": profile.created_at or "",
    }


@router.patch("/api/v1/admin/users/{user_id}/status")
async def update_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    before = await services.admin.user(user_id) if not services.settings.allow_mock_services else None
    profile = await services.profiles.set_status(user_id, payload.status)
    await services.admin.audit(
        admin.id,
        "user.status.changed",
        "profile",
        user_id,
        before,
        profile.model_dump(mode="json"),
        request.state.request_id,
    )
    return profile


# ── CRUD User Endpoints ──


@router.post("/api/admin/users", status_code=201)
async def create_user(
    payload: CreateUserRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    auth_user = await services.auth.admin_create_user(payload.email, payload.password)
    user_id = auth_user["id"]
    profile = await services.admin.create_user_profile(
        user_id=user_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role.value,
        instansi=payload.instansi,
    )
    await services.admin.audit(
        admin.id, "user.created", "profile", user_id,
        None, {"email": payload.email, "full_name": payload.full_name, "role": payload.role.value},
        request.state.request_id,
    )
    return profile


@router.patch("/api/admin/users/{user_id}")
async def update_user(
    user_id: str,
    payload: UpdateUserRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    # Self-demotion guard
    if payload.role is not None and user_id == admin.id and payload.role != ApplicationRole.ADMIN:
        raise ForbiddenError("Tidak dapat menurunkan role akun sendiri.")

    # Self-status guard
    if payload.account_status is not None and user_id == admin.id:
        raise ForbiddenError("Tidak dapat mengubah status akun sendiri.")

    before = await services.admin.user(user_id) if not services.settings.allow_mock_services else None

    update_data: dict = {}
    if payload.full_name is not None:
        update_data["full_name"] = payload.full_name
    if payload.instansi is not None:
        update_data["instansi"] = payload.instansi
    if payload.role is not None:
        update_data["application_role"] = payload.role.value
    if payload.account_status is not None:
        update_data["account_status"] = payload.account_status.value

    if not update_data:
        raise AppError("VALIDATION_ERROR", "Tidak ada field yang diubah.", 400)

    result = await services.admin.update_user(user_id, update_data)
    await services.admin.audit(
        admin.id, "user.updated", "profile", user_id,
        {k: before.get(k) for k in update_data} if before else None,
        update_data,
        request.state.request_id,
    )
    return result


@router.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    payload: DeleteUserRequest | None = None,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    if user_id == admin.id:
        raise ForbiddenError("Tidak dapat menghapus akun sendiri.")

    before = await services.admin.user(user_id) if not services.settings.allow_mock_services else None
    if before and before.get("account_status") == "deleted":
        raise AppError("VALIDATION_ERROR", "Pengguna sudah dihapus.", 400)

    result = await services.admin.soft_delete_user(user_id, admin.id)
    await services.admin.audit(
        admin.id, "user.deleted", "profile", user_id,
        {"account_status": before.get("account_status")} if before else None,
        {"account_status": "deleted", "reason": payload.reason if payload else None},
        request.state.request_id,
    )
    return {"message": "Pengguna berhasil dihapus.", "user": result}


@router.post("/api/admin/users/{user_id}/restore")
async def restore_user(
    user_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    before = await services.admin.user(user_id) if not services.settings.allow_mock_services else None
    if before and before.get("account_status") != "deleted":
        raise AppError("VALIDATION_ERROR", "Pengguna tidak dalam status dihapus.", 400)

    result = await services.admin.restore_user(user_id)
    await services.admin.audit(
        admin.id, "user.restored", "profile", user_id,
        {"account_status": "deleted"},
        {"account_status": "active"},
        request.state.request_id,
    )
    return {"message": "Pengguna berhasil dipulihkan.", "user": result}


@router.get("/api/v1/admin/usage/features")
async def feature_usage(
    date_from: str | None = None,
    date_to: str | None = None,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    return await services.admin.feature_usage(date_from, date_to)


@router.get("/api/admin/model-usage")
@router.get("/api/v1/admin/usage/models", include_in_schema=False)
async def model_usage(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    try:
        return await services.admin.get_model_usage()
    except Exception as exc:
        logger.exception("Failed to get model usage")
        return {
            "total_requests": 0,
            "avg_latency_ms": 0.0,
            "error_rate": 0.0,
            "entries": [],
            "summary": {
                "total_requests": 0,
                "total_tokens": 0,
                "total_prompt_tokens": 0,
                "total_completion_tokens": 0,
                "text_model_requests": 0,
                "vision_model_requests": 0,
                "failed_requests": 0
            },
            "by_model": [],
            "daily_usage": [],
            "recent_requests": []
        }


@router.get("/api/admin/storage-stats")
@router.get("/api/v1/admin/usage/storage", include_in_schema=False)
async def storage_usage(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    try:
        return await services.admin.get_storage_stats(services)
    except Exception as exc:
        logger.exception("Failed to get storage stats")
        return {
            "status": "unavailable",
            "buckets": [],
            "total_size_bytes": 0,
            "failed_uploads": 0,
            "summary": {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_attachments": 0,
                "image_files": 0,
                "document_files": 0,
                "failed_processing": 0
            },
            "by_mime_type": [],
            "recent_files": []
        }


@router.get("/api/v1/admin/audit-logs")
async def audit_logs(admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)):
    return await services.admin.audit_logs()


@router.get("/api/admin/health")
@router.get("/api/v1/admin/system-health", include_in_schema=False)
async def health(admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)):
    try:
        return await services.admin.get_system_health(services)
    except Exception as exc:
        logger.exception("Failed to get system health")
        return {
            "overall": "degraded",
            "services": {
                "fastapi": {"status": "ok", "message": "Connected"},
                "supabase": {"status": "down", "message": f"Error: {str(exc)}"},
                "neo4j": {"status": "unknown", "message": "Not checkable"},
                "minio": {"status": "unknown", "message": "Not checkable"},
                "llm_text": {"status": "down", "message": "Text model unavailable"},
                "llm_vlm": {"status": "down", "message": "Vision model unavailable"}
            }
        }


@router.get("/api/admin/graph-stats")
async def graph_stats(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    try:
        return await services.admin.get_graph_stats(services)
    except Exception as exc:
        logger.exception("Failed to get graph stats")
        return {
            "status": "unavailable",
            "herb_count": 0,
            "compound_count": 0,
            "traditional_use_count": 0,
            "preparation_method_count": 0,
            "usage_guideline_count": 0,
            "safety_warning_count": 0,
            "source_count": 0,
            "fulltext_index_status": "unknown",
            "neo4j_latency_ms": 0,
            "last_enrichment_at": None,
            "summary": {
                "total_nodes": 0,
                "total_relationships": 0,
                "herbs": 0,
                "compounds": 0,
                "benefits": 0,
                "sources": 0
            },
            "labels": [],
            "relationships": [],
            "message": f"Error: {str(exc)}"
        }


@router.get("/api/admin/recommendation-analytics")
async def recommendation_analytics(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    try:
        return await services.admin.get_recommendation_analytics()
    except Exception as exc:
        logger.exception("Failed to get recommendation analytics")
        return {
            "total_sessions": 0,
            "top_complaints": [],
            "top_herbs": [],
            "no_result_rate": 0.0,
            "avg_latency_ms": 0.0,
            "failure_rate": 0.0,
            "common_warnings": [],
            "summary": {
                "total_recommendations": 0,
                "total_searches": 0,
                "top_herbs": [],
                "top_symptoms": [],
                "success_rate": 0.0
            },
            "daily": [],
            "recent": []
        }


@router.get("/api/admin/quiz-analytics")
async def quiz_analytics(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    try:
        return await services.admin.get_quiz_analytics()
    except Exception as exc:
        logger.exception("Failed to get quiz analytics")
        return {
            "total_sessions": 0,
            "completion_rate": 0.0,
            "avg_score": 0.0,
            "top_weak_topics": [],
            "daily_active_learners": 0,
            "summary": {
                "total_modules": 0,
                "total_levels": 0,
                "total_questions": 0,
                "total_attempts": 0,
                "completed_attempts": 0,
                "average_score": 0.0,
                "total_answers": 0
            },
            "by_topic": [],
            "by_level": [],
            "recent_attempts": []
        }


@router.get("/api/admin/errors")
async def errors(
    limit: int = Query(50, ge=1, le=200),
    unresolved_only: bool = Query(False),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services)
):
    try:
        return await services.admin.get_recent_errors(limit, unresolved_only)
    except Exception as exc:
        logger.exception("Failed to get error logs")
        return {
            "errors": [],
            "total": 0,
            "unresolved_count": 0,
            "summary": {
                "total_errors": 0,
                "unresolved_errors": 0,
                "last_24h": 0
            },
            "items": []
        }
