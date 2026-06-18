from typing import Any
from app.services.supabase.admin_service import AdminService


class ActivityService:
    def __init__(self, admin: AdminService):
        self.admin = admin

    async def emit(self, user_id: str | None, event_name: str, **metadata: Any) -> None:
        try:
            await self.admin.track(user_id, event_name, metadata)
        except Exception:
            return
