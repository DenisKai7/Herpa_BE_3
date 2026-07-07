import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import StreamingResponse

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.models.ai_usage import (
    AIUsageBulkDeleteByFilterRequest,
    AIUsageDeleteRequest,
)
from app.models.auth import CurrentUser

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Admin AI Usage"])


# ── Static routes MUST come before parameterized routes ──
# Otherwise FastAPI tries to match /dashboard against /{log_id} first,
# fails int conversion, and returns 422.


@router.get("/api/admin/ai-usage/dashboard")
async def get_ai_usage_dashboard(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get AI usage dashboard statistics."""
    logger.info("ai_usage_dashboard_request", extra={"date_from": date_from, "date_to": date_to})
    try:
        result = await services.admin_ai_usage.get_dashboard_stats(date_from=date_from, date_to=date_to)
        logger.info("ai_usage_dashboard_success", extra={"total_requests": result.get("total_requests", 0)})
        return result
    except Exception as exc:
        logger.error("ai_usage_dashboard_error", extra={"error": str(exc)})
        return {
            "total_requests": 0,
            "total_tokens_input": 0,
            "total_tokens_output": 0,
            "total_tokens": 0,
            "active_users": 0,
            "error_rate": 0.0,
            "avg_latency_ms": 0.0,
            "active_models": 0,
            "active_personas": 0,
        }


@router.get("/api/admin/ai-usage/charts")
async def get_ai_usage_charts(
    days: int = Query(30, ge=1, le=365),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get AI usage charts data."""
    logger.info("ai_usage_charts_request", extra={"days": days, "date_from": date_from, "date_to": date_to})
    try:
        result = await services.admin_ai_usage.get_charts_data(days=days, date_from=date_from, date_to=date_to)
        logger.info("ai_usage_charts_success")
        return result
    except Exception as exc:
        logger.error("ai_usage_charts_error", extra={"error": str(exc)})
        return {
            "daily_requests": [],
            "daily_tokens": [],
            "by_persona": [],
            "by_model": [],
            "hourly_heatmap": [],
            "top_users": [],
            "top_endpoints": [],
            "error_analytics": {"by_endpoint": [], "by_model": [], "by_day": []},
            "latency_stats": {"min": 0, "max": 0, "avg": 0, "median": 0, "p95": 0},
            "cost_estimation": {"total_tokens": 0, "total_latency_ms": 0, "throughput_tokens_per_sec": 0, "provider": "local"},
        }


@router.get("/api/admin/ai-usage/export/csv")
async def export_ai_usage_csv(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user_id: str | None = Query(None),
    persona: str | None = Query(None),
    model_name: str | None = Query(None),
    endpoint: str | None = Query(None),
    status: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export AI usage logs as CSV."""
    csv_content = await services.admin_ai_usage.export_csv(
        date_from=date_from, date_to=date_to, user_id=user_id,
        persona=persona, model_name=model_name, endpoint=endpoint, status=status,
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ai_usage_logs.csv"},
    )


@router.get("/api/admin/ai-usage/export/excel")
async def export_ai_usage_excel(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user_id: str | None = Query(None),
    persona: str | None = Query(None),
    model_name: str | None = Query(None),
    endpoint: str | None = Query(None),
    status: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export AI usage logs as Excel."""
    excel_content = await services.admin_ai_usage.export_excel(
        date_from=date_from, date_to=date_to, user_id=user_id,
        persona=persona, model_name=model_name, endpoint=endpoint, status=status,
    )
    return StreamingResponse(
        iter([excel_content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ai_usage_logs.xlsx"},
    )


@router.get("/api/admin/ai-usage/export/pdf")
async def export_ai_usage_pdf(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    user_id: str | None = Query(None),
    persona: str | None = Query(None),
    model_name: str | None = Query(None),
    endpoint: str | None = Query(None),
    status: str | None = Query(None),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Export AI usage logs as PDF."""
    pdf_content = await services.admin_ai_usage.export_pdf(
        date_from=date_from, date_to=date_to, user_id=user_id,
        persona=persona, model_name=model_name, endpoint=endpoint, status=status,
    )
    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=ai_usage_logs.pdf"},
    )


@router.get("/api/admin/ai-usage")
async def list_ai_usage(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    search: str | None = Query(None, max_length=200),
    user_id: str | None = Query(None),
    persona: str | None = Query(None),
    model_name: str | None = Query(None),
    endpoint: str | None = Query(None),
    provider: str | None = Query(None),
    status: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    sort: Literal["created_at", "latency_ms", "input_tokens", "output_tokens", "model_name"] = Query("created_at"),
    sort_dir: Literal["asc", "desc"] = Query("desc"),
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """List AI usage logs with pagination, filtering, and sorting."""
    rows, total = await services.admin_ai_usage.list_logs(
        limit=limit,
        offset=offset,
        search=search,
        user_id=user_id,
        persona=persona,
        model_name=model_name,
        endpoint=endpoint,
        provider=provider,
        status=status,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        sort_dir=sort_dir,
    )
    return {"logs": rows, "total": total, "limit": limit, "offset": offset}


# ── Parameterized routes AFTER static routes ──


@router.get("/api/admin/ai-usage/{log_id}")
async def get_ai_usage_detail(
    log_id: int,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Get single AI usage log detail."""
    return await services.admin_ai_usage.get_log(log_id)


@router.delete("/api/admin/ai-usage/{log_id}")
async def delete_ai_usage(
    log_id: int,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Soft delete a single AI usage log."""
    result = await services.admin_ai_usage.soft_delete(log_id, admin.id)
    await services.admin.audit(
        admin.id, "ai_usage.deleted", "model_usage_events", str(log_id),
        None, {"deleted": True}, request.state.request_id,
    )
    return {"message": "Log berhasil dihapus.", "log": result}


@router.delete("/api/admin/ai-usage/bulk")
async def bulk_delete_ai_usage(
    payload: AIUsageDeleteRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Bulk soft delete AI usage logs by IDs."""
    count = await services.admin_ai_usage.bulk_delete(payload.ids, admin.id)
    await services.admin.audit(
        admin.id, "ai_usage.bulk_deleted", "model_usage_events", "bulk",
        None, {"ids": payload.ids, "deleted_count": count}, request.state.request_id,
    )
    return {"message": f"{count} log berhasil dihapus.", "deleted_count": count}


@router.post("/api/admin/ai-usage/delete-by-filter")
async def delete_ai_usage_by_filter(
    payload: AIUsageBulkDeleteByFilterRequest,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
):
    """Delete AI usage logs by filter criteria."""
    count = await services.admin_ai_usage.delete_by_filter(
        admin_id=admin.id,
        user_id=payload.user_id,
        persona=payload.persona,
        model_name=payload.model_name,
        endpoint=payload.endpoint,
        date_from=payload.date_from,
        date_to=payload.date_to,
        status=payload.status,
    )
    await services.admin.audit(
        admin.id, "ai_usage.filter_deleted", "model_usage_events", "filter",
        None, {"filter": payload.model_dump(), "deleted_count": count}, request.state.request_id,
    )
    return {"message": f"{count} log berhasil dihapus.", "deleted_count": count}
