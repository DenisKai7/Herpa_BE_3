from typing import Annotated
from fastapi import Depends
from app.api.dependencies.auth import get_current_user
from app.core.constants import ApplicationRole
from app.core.exceptions import ForbiddenError
from app.models.auth import CurrentUser


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    if user.application_role != ApplicationRole.ADMIN:
        raise ForbiddenError("Endpoint ini hanya untuk admin.")
    return user
