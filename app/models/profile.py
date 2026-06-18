from pydantic import BaseModel, Field
from app.core.constants import AccountStatus, ApplicationRole, Persona


class Profile(BaseModel):
    id: str
    email: str = ""
    username: str | None = None
    full_name: str | None = None
    application_role: ApplicationRole = ApplicationRole.USER
    persona: Persona = Persona.UMUM
    account_status: AccountStatus = AccountStatus.ACTIVE
    avatar_object_key: str | None = None
    storage_quota_bytes: int = 104857600
    created_at: str | None = None
    updated_at: str | None = None
    last_active_at: str | None = None
    instansi: str | None = None
    provinsi: str | None = None
    kota: str | None = None


class PersonaUpdate(BaseModel):
    persona: Persona


class AvatarCompleteRequest(BaseModel):
    object_key: str = Field(min_length=1)
    content_type: str
    size_bytes: int = Field(ge=1)
