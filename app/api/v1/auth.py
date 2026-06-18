from typing import Annotated
from fastapi import APIRouter, Depends, File, UploadFile
from app.api.dependencies.auth import get_access_token, get_current_user
from app.api.dependencies.services import Services, get_services
from app.models.auth import (
    AuthResponse,
    ChangePasswordRequest,
    CurrentUser,
    LoginRequest,
    RegisterRequest,
    UpdateProfileRequest,
)

router = APIRouter(tags=["Authentication"])


@router.post("/api/auth/login", response_model=AuthResponse)
@router.post("/api/v1/auth/login", response_model=AuthResponse, include_in_schema=False)
async def login(payload: LoginRequest, services: Annotated[Services, Depends(get_services)]) -> AuthResponse:
    if services.settings.allow_mock_services:
        token = "dev-admin" if payload.email.startswith("admin") else "dev-user"
        uid = (
            "00000000-0000-0000-0000-000000000001"
            if token == "dev-admin"
            else "00000000-0000-0000-0000-000000000002"
        )
        profile = await services.profiles.get(uid, payload.email)
        if token == "dev-admin":
            profile = await services.profiles.set_role(uid, "admin")
        user = CurrentUser(
            id=profile.id,
            email=payload.email,
            role=profile.application_role,
            application_role=profile.application_role,
            persona=profile.persona,
            account_status=profile.account_status,
            created_at=profile.created_at,
        )
        return AuthResponse(token=token, user=user)
    result = await services.auth.login(str(payload.email), payload.password)
    auth_user = result["user"]
    profile = await services.profiles.get(auth_user["id"], auth_user.get("email", ""))
    user = CurrentUser(
        id=profile.id,
        email=auth_user.get("email", ""),
        username=profile.username,
        full_name=profile.full_name,
        nama=profile.full_name,
        role=profile.application_role,
        application_role=profile.application_role,
        persona=profile.persona,
        account_status=profile.account_status,
        created_at=profile.created_at,
    )
    return AuthResponse(token=result["access_token"], refresh_token=result.get("refresh_token"), user=user)


@router.post("/api/auth/register", response_model=AuthResponse)
@router.post("/api/v1/auth/register", response_model=AuthResponse, include_in_schema=False)
async def register(
    payload: RegisterRequest, services: Annotated[Services, Depends(get_services)]
) -> AuthResponse:
    if services.settings.allow_mock_services:
        uid = "00000000-0000-0000-0000-000000000002"
        profile = await services.profiles.upsert_from_auth(
            {"id": uid, "email": str(payload.email), "user_metadata": payload.model_dump()}
        )
        return AuthResponse(
            token="dev-user",
            user=CurrentUser(
                id=uid,
                email=str(payload.email),
                username=profile.username,
                full_name=profile.full_name,
                nama=profile.full_name,
                role=profile.application_role,
                application_role=profile.application_role,
                persona=profile.persona,
                account_status=profile.account_status,
                created_at=profile.created_at,
            ),
        )
    result = await services.auth.register(payload.model_dump())
    auth_user = result.get("user") or result
    profile = await services.profiles.upsert_from_auth(auth_user)
    return AuthResponse(
        token=result.get("access_token", "") or "",
        refresh_token=result.get("refresh_token"),
        user=CurrentUser(
            id=profile.id,
            email=profile.email,
            username=profile.username,
            full_name=profile.full_name,
            nama=profile.full_name,
            role=profile.application_role,
            application_role=profile.application_role,
            persona=profile.persona,
            account_status=profile.account_status,
            created_at=profile.created_at,
        ),
    )


@router.get("/api/auth/me", response_model=CurrentUser)
@router.get("/api/v1/auth/me", response_model=CurrentUser, include_in_schema=False)
async def me(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    return user


@router.put("/api/auth/me", response_model=CurrentUser)
@router.patch("/api/v1/profiles/me", response_model=CurrentUser, include_in_schema=False)
async def update_me(
    payload: UpdateProfileRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    services: Annotated[Services, Depends(get_services)],
) -> CurrentUser:
    data = payload.model_dump(exclude_none=True)
    if "nama" in data and "full_name" not in data:
        data["full_name"] = data.pop("nama")
    profile = await services.profiles.update(user.id, data)
    return user.model_copy(
        update={
            "username": profile.username,
            "full_name": profile.full_name,
            "nama": profile.full_name,
            "persona": profile.persona,
            "instansi": profile.instansi,
            "provinsi": profile.provinsi,
            "kota": profile.kota,
        }
    )


@router.put("/api/auth/me/password", status_code=204)
async def change_password(
    payload: ChangePasswordRequest,
    token: Annotated[str, Depends(get_access_token)],
    services: Annotated[Services, Depends(get_services)],
) -> None:
    if not services.settings.allow_mock_services:
        await services.auth.change_password(token, payload.new_password)


@router.put("/api/auth/me/avatar", response_model=CurrentUser)
async def upload_avatar(
    avatar: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> CurrentUser:
    uploaded = await services.attachments.upload(user.id, avatar, "Foto profil pengguna")
    await services.profiles.update(user.id, {"avatar_object_key": uploaded.attachment.stored_filename})
    return user.model_copy(update={"avatar_url": uploaded.url})
