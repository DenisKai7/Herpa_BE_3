from typing import Literal

from pydantic import BaseModel, EmailStr, Field
from app.core.constants import AccountStatus, ApplicationRole


class AdminAnalytics(BaseModel):
    total_users: int = 0
    total_messages: int = 0
    total_chats: int = 0
    active_users_today: int = 0
    messages_today: int = 0
    total_recommendations: int = 0
    total_attachments: int = 0
    total_quiz_attempts: int = 0
    error_rate: float = 0
    average_latency_ms: float = 0


class AdminUser(BaseModel):
    id: str
    email: str = ""
    full_name: str = ""
    role: ApplicationRole = ApplicationRole.USER
    persona: str = "umum"
    account_status: AccountStatus = AccountStatus.ACTIVE
    instansi: str = ""
    last_active_at: str | None = None
    created_at: str = ""
    deleted_at: str | None = None
    deleted_by: str | None = None


class UpdateUserRoleRequest(BaseModel):
    user_id: str
    role: ApplicationRole


class UpdateUserStatusRequest(BaseModel):
    status: AccountStatus


# ── CRUD models ──


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=200)
    instansi: str | None = None
    role: ApplicationRole = ApplicationRole.USER


class UpdateUserRequest(BaseModel):
    full_name: str | None = Field(None, min_length=1, max_length=200)
    instansi: str | None = None
    role: ApplicationRole | None = None
    account_status: AccountStatus | None = None


class DeleteUserRequest(BaseModel):
    reason: str | None = None


class UserListResponse(BaseModel):
    users: list[AdminUser] = []
    total: int = 0
    limit: int = 20
    offset: int = 0
