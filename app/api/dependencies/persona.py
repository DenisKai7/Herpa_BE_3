from typing import Annotated
from fastapi import Depends
from app.api.dependencies.auth import get_current_user
from app.models.auth import CurrentUser


async def resolve_persona(user: Annotated[CurrentUser, Depends(get_current_user)]) -> str:
    return user.persona.value
