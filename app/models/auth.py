from pydantic import BaseModel, EmailStr, Field
from app.core.constants import AccountStatus, ApplicationRole, Persona


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    username: str = Field(min_length=3, max_length=50)
    nama: str = Field(min_length=2, max_length=120)
    instansi: str = ""
    provinsi: str = ""
    kota: str = ""


class CurrentUser(BaseModel):
    id: str
    email: str = ""
    username: str | None = None
    nama: str | None = None
    full_name: str | None = None
    role: ApplicationRole = ApplicationRole.USER
    application_role: ApplicationRole = ApplicationRole.USER
    persona: Persona = Persona.UMUM
    account_status: AccountStatus = AccountStatus.ACTIVE
    instansi: str | None = None
    provinsi: str | None = None
    kota: str | None = None
    avatar_url: str | None = None
    created_at: str | None = None


class AuthResponse(BaseModel):
    token: str
    refresh_token: str | None = None
    user: CurrentUser


class UpdateProfileRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    full_name: str | None = Field(default=None, max_length=120)
    nama: str | None = Field(default=None, max_length=120)
    instansi: str | None = Field(default=None, max_length=160)
    provinsi: str | None = Field(default=None, max_length=100)
    kota: str | None = Field(default=None, max_length=100)
    persona: Persona | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
