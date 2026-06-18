from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.models.admin import AdminAnalytics, UpdateUserRoleRequest, UpdateUserStatusRequest
from app.models.auth import CurrentUser

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
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    return await services.admin.users(limit, offset)


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


@router.get("/api/v1/admin/usage/features")
async def feature_usage(
    date_from: str | None = None,
    date_to: str | None = None,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    return await services.admin.feature_usage(date_from, date_to)


@router.get("/api/v1/admin/usage/models")
async def model_usage(
    admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)
):
    return await services.admin.model_usage()


@router.get("/api/v1/admin/usage/storage")
async def storage_usage(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> dict:
    if services.settings.allow_mock_services:
        return {"total_bytes": 0, "objects": 0, "buckets": {}}
    rows = await services.supabase.request("POST", "rpc/admin_storage_summary", json={})
    return rows or {"total_bytes": 0, "objects": 0, "buckets": {}}


@router.get("/api/v1/admin/audit-logs")
async def audit_logs(admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)):
    return await services.admin.audit_logs()


@router.get("/api/v1/admin/system-health")
async def health(admin: CurrentUser = Depends(require_admin), services: Services = Depends(get_services)):
    return {
        "supabase": await services.supabase.health(),
        "neo4j": await services.neo4j.health(),
        "minio": await services.storage.health(),
        "models": await services.model_gateway.health(),
    }
