from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.models.attachment import (
    AttachmentCompleteRequest,
    AttachmentStatusResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.models.auth import CurrentUser
from app.models.profile import PersonaUpdate, Profile

router = APIRouter(prefix="/api/v1/profiles", tags=["Profiles"])


@router.get("/me", response_model=Profile)
async def profile(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> Profile:
    return await services.profiles.get(user.id, user.email)


@router.patch("/me/persona", response_model=Profile)
async def change_persona(
    payload: PersonaUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> Profile:
    return await services.profiles.update(user.id, {"persona": payload.persona.value})


@router.post("/me/avatar/presign-upload", response_model=PresignUploadResponse)
async def presign_avatar(
    payload: PresignUploadRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> PresignUploadResponse:
    return await services.attachments.presign(user.id, payload.model_copy(update={"purpose": "avatar"}))


@router.post("/me/avatar/complete", response_model=AttachmentStatusResponse)
async def complete_avatar(
    payload: AttachmentCompleteRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> AttachmentStatusResponse:
    current = await services.profiles.get(user.id, user.email)
    result = await services.attachments.complete(user.id, payload)
    if current.avatar_object_key and current.avatar_object_key != payload.object_key:
        await services.storage.delete(services.settings.minio_profile_bucket, current.avatar_object_key)
    await services.profiles.update(user.id, {"avatar_object_key": payload.object_key})
    return result
