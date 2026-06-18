from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies.roles import require_admin
from app.api.dependencies.services import Services, get_services
from app.core.exceptions import NotFoundError
from app.models.auth import CurrentUser

router = APIRouter(prefix="/api/v1/admin/storage", tags=["Admin Storage"])


@router.get("/summary")
async def summary(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> dict:
    if services.settings.allow_mock_services:
        return {"total_bytes": 0, "objects": 0, "buckets": {}}
    rows = await services.supabase.request("POST", "rpc/admin_storage_summary", json={})
    return rows or {"total_bytes": 0, "objects": 0, "buckets": {}}


@router.get("/objects")
async def objects(
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> list[dict]:
    if services.settings.allow_mock_services:
        return []
    return await services.supabase.select(
        "storage_objects",
        {"select": "*", "deleted_at": "is.null", "order": "created_at.desc", "limit": "1000"},
    )


@router.delete("/objects/{object_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_object(
    object_id: str,
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> Response:
    if services.settings.allow_mock_services:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    rows = await services.supabase.select(
        "storage_objects",
        {"select": "*", "id": f"eq.{object_id}", "deleted_at": "is.null", "limit": "1"},
    )
    if not rows:
        raise NotFoundError("Objek storage tidak ditemukan.")
    row = rows[0]
    await services.storage.delete(row["bucket"], row["object_key"])
    await services.supabase.update(
        "storage_objects",
        {"id": f"eq.{object_id}"},
        {"deleted_at": datetime.now(timezone.utc).isoformat()},
    )
    await services.admin.audit(
        admin.id,
        "storage.object.deleted",
        "storage_object",
        object_id,
        row,
        None,
        request.state.request_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cleanup-orphans")
async def cleanup_orphans(
    request: Request,
    admin: CurrentUser = Depends(require_admin),
    services: Services = Depends(get_services),
) -> dict:
    if services.settings.allow_mock_services:
        return {"scanned": 0, "deleted": 0, "objects": []}
    rows = await services.supabase.select(
        "storage_objects",
        {"select": "bucket,object_key", "deleted_at": "is.null", "limit": "10000"},
    )
    known = {(row["bucket"], row["object_key"]) for row in rows}
    deleted: list[dict[str, str]] = []
    scanned = 0
    for bucket in [
        services.settings.minio_profile_bucket,
        services.settings.minio_attachment_bucket,
        services.settings.minio_export_bucket,
        services.settings.minio_temp_bucket,
    ]:
        for item in await services.storage.list_keys(bucket):
            scanned += 1
            key = str(item["object_name"])
            if (bucket, key) not in known:
                await services.storage.delete(bucket, key)
                deleted.append({"bucket": bucket, "object_key": key})
    await services.admin.audit(
        admin.id,
        "storage.cleanup_orphans",
        "storage",
        "all",
        None,
        {"scanned": scanned, "deleted": len(deleted)},
        request.state.request_id,
    )
    return {"scanned": scanned, "deleted": len(deleted), "objects": deleted}
