import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin Recommendations"])


@router.get("/api/admin/recommendations")
async def list_recommendations(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: Literal["created_at", "status"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """List recommendation sessions with pagination and filters."""
    rows, total = await services.admin_recommendation.list_sessions(
        limit=limit, offset=offset, search=search, status=status,
        date_from=date_from, date_to=date_to, sort=sort, sort_dir=sort_dir,
    )
    return {"sessions": rows, "total": total, "limit": limit, "offset": offset}


@router.get("/api/admin/recommendations/{session_id}")
async def get_recommendation(
    session_id: str,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get single recommendation session with results."""
    result = await services.admin_recommendation.get_session(session_id)
    if not result:
        return {"error": "Session not found"}
    return result


@router.delete("/api/admin/recommendations/{session_id}")
async def delete_recommendation(
    session_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Delete a recommendation session."""
    ok = await services.admin_recommendation.delete_session(session_id)
    await services.admin.audit(
        admin.id, "recommendation.deleted", "recommendation_sessions", session_id,
        None, {"deleted": ok}, request.state.request_id,
    )
    return {"message": "Session berhasil dihapus." if ok else "Gagal menghapus session."}


@router.get("/api/admin/recommendations/dashboard")
async def recommendation_dashboard(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get recommendation dashboard statistics."""
    return await services.admin_recommendation.get_dashboard_stats()


@router.get("/api/admin/recommendations/charts")
async def recommendation_charts(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get recommendation charts data."""
    return await services.admin_recommendation.get_charts_data()


@router.get("/api/admin/recommendations/export/csv")
async def export_csv(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export recommendation sessions as CSV."""
    csv_content = await services.admin_recommendation.export_csv()
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=recommendations.csv"},
    )
