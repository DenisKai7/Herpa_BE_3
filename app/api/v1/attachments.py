from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.core.rate_limit import rate_limiter
from app.models.attachment import (
    AttachmentCompleteRequest,
    AttachmentStatusResponse,
    FileUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
    VisionDebugResponse,
)
from app.models.auth import CurrentUser

router = APIRouter(tags=["Attachments"])


@router.post("/api/files/upload", response_model=FileUploadResponse)
@router.post("/api/v1/attachments/upload", response_model=FileUploadResponse, include_in_schema=False)
async def upload(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> FileUploadResponse:
    rate_limiter.check(f"upload:{user.id}", services.settings.rate_limit_upload_per_minute)
    return await services.attachments.upload(user.id, file)


@router.post("/api/v1/attachments/presign-upload", response_model=PresignUploadResponse)
async def presign(
    payload: PresignUploadRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> PresignUploadResponse:
    rate_limiter.check(f"upload:{user.id}", services.settings.rate_limit_upload_per_minute)
    return await services.attachments.presign(user.id, payload)


@router.post("/api/v1/attachments/complete", response_model=AttachmentStatusResponse)
async def complete(
    payload: AttachmentCompleteRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> AttachmentStatusResponse:
    return await services.attachments.complete(user.id, payload)


@router.get("/api/files/{attachment_id}/status", response_model=AttachmentStatusResponse)
@router.get(
    "/api/v1/attachments/{attachment_id}", response_model=AttachmentStatusResponse, include_in_schema=False
)
async def attachment_status(
    attachment_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> AttachmentStatusResponse:
    return await services.attachments.status(user.id, attachment_id)


@router.post("/api/files/{attachment_id}/retry", response_model=AttachmentStatusResponse)
async def retry(
    attachment_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> AttachmentStatusResponse:
    return await services.attachments.retry(user.id, attachment_id)


@router.get("/api/files/{attachment_id}/vision-debug", response_model=VisionDebugResponse)
async def vision_debug(
    attachment_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> VisionDebugResponse:
    row = await services.attachments._row(user.id, attachment_id)
    meta = row.get("extraction_metadata") or {}
    visual_analysis = {
        "visual_summary": meta.get("visual_summary", ""),
        "plant_candidates": meta.get("plant_candidates", []),
        "not_likely": meta.get("not_likely", []),
        "limitations": meta.get("limitations", []),
        "clarification_questions": meta.get("clarification_questions", []),
    }
    created_at = row.get("created_at")
    created_at_str = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at) if created_at else None

    return VisionDebugResponse(
        attachment_id=attachment_id,
        mime_type=row.get("mime_type", ""),
        processing_status=row.get("processing_status", ""),
        visual_analysis=visual_analysis,
        vlm_called=meta.get("vlm_failed") is False or bool(meta.get("plant_candidates")),
        vlm_model=services.settings.llama_vision_model_name,
        last_processed_at=created_at_str,
        content_hash=row.get("content_hash") or meta.get("image_sha256"),
    )


@router.post("/api/files/{attachment_id}/reprocess-vision", response_model=AttachmentStatusResponse)
async def reprocess_vision(
    attachment_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> AttachmentStatusResponse:
    return await services.attachments.reprocess_vision(user.id, attachment_id)


@router.delete("/api/v1/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    attachment_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> Response:
    await services.attachments.delete(user.id, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
