from typing import Annotated
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.api.dependencies.services import Services, get_services
from app.core.constants import AccountStatus
from app.core.exceptions import AppError, UnauthorizedError
from app.models.auth import CurrentUser

bearer = HTTPBearer(auto_error=False)


async def get_access_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str:
    if not credentials:
        raise UnauthorizedError()
    return credentials.credentials


async def get_current_user(
    token: Annotated[str, Depends(get_access_token)], services: Annotated[Services, Depends(get_services)]
) -> CurrentUser:
    if services.settings.allow_mock_services:
        role = "admin" if token == "dev-admin" else "user"
        uid = (
            "00000000-0000-0000-0000-000000000001"
            if role == "admin"
            else "00000000-0000-0000-0000-000000000002"
        )
        profile = await services.profiles.get(uid, f"{role}@local.test")
        if profile.application_role.value != role:
            profile = await services.profiles.set_role(uid, role)
        return CurrentUser(
            id=uid,
            email=profile.email,
            username=profile.username,
            full_name=profile.full_name,
            nama=profile.full_name,
            role=profile.application_role,
            application_role=profile.application_role,
            persona=profile.persona,
            account_status=profile.account_status,
            instansi=profile.instansi,
            provinsi=profile.provinsi,
            kota=profile.kota,
            created_at=profile.created_at,
        )
    auth_user = await services.auth.verify_token_remote(token)
    profile = await services.profiles.get(auth_user["id"], auth_user.get("email", ""))
    if profile.account_status != AccountStatus.ACTIVE:
        raise AppError("ACCOUNT_SUSPENDED", "Akun tidak aktif.", 403)
    return CurrentUser(
        id=profile.id,
        email=auth_user.get("email") or profile.email,
        username=profile.username,
        full_name=profile.full_name,
        nama=profile.full_name,
        role=profile.application_role,
        application_role=profile.application_role,
        persona=profile.persona,
        account_status=profile.account_status,
        instansi=profile.instansi,
        provinsi=profile.provinsi,
        kota=profile.kota,
        created_at=profile.created_at,
    )
