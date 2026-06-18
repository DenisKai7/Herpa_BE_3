from pydantic import BaseModel
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
    role: ApplicationRole
    persona: str = "umum"
    account_status: AccountStatus = AccountStatus.ACTIVE
    instansi: str = ""
    created_at: str = ""


class UpdateUserRoleRequest(BaseModel):
    user_id: str
    role: ApplicationRole


class UpdateUserStatusRequest(BaseModel):
    status: AccountStatus
