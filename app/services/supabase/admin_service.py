from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import NotFoundError
from app.services.supabase.client import SupabaseClient


class AdminService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def analytics(self) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            return {
                "total_users": 0,
                "total_messages": 0,
                "total_chats": 0,
                "active_users_today": 0,
                "messages_today": 0,
                "total_recommendations": 0,
                "total_attachments": 0,
                "total_quiz_attempts": 0,
                "error_rate": 0.0,
                "average_latency_ms": 0.0,
            }
        rows = await self.client.request("POST", "rpc/admin_dashboard_overview", json={})
        return rows[0] if isinstance(rows, list) and rows else rows

    async def users(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        rows = await self.client.select(
            "profiles",
            {
                "select": "id,email,full_name,application_role,persona,account_status,instansi,created_at,last_active_at",
                "order": "created_at.desc",
                "limit": str(min(limit, 200)),
                "offset": str(max(offset, 0)),
            },
        )
        for row in rows:
            row["role"] = row.get("application_role", "user")
        return rows

    async def user(self, user_id: str) -> dict[str, Any]:
        if self.client.settings.allow_mock_services:
            raise NotFoundError("Pengguna mock tidak ditemukan.")
        rows = await self.client.select("profiles", {"select": "*", "id": f"eq.{user_id}", "limit": "1"})
        if not rows:
            raise NotFoundError("Pengguna tidak ditemukan.")
        return rows[0]

    async def feature_usage(
        self, date_from: str | None = None, date_to: str | None = None
    ) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        params: dict[str, Any] = {
            "select": "event_name,persona,success,latency_ms,created_at",
            "order": "created_at.desc",
            "limit": "5000",
        }
        if date_from:
            params["created_at"] = f"gte.{date_from}"
        if date_to:
            params["and"] = f"(created_at.lte.{date_to})"
        return await self.client.select("feature_usage_events", params)

    async def model_usage(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        return await self.client.select(
            "model_usage_events",
            {
                "select": "model_name,input_tokens,output_tokens,latency_ms,success,error_code,created_at",
                "order": "created_at.desc",
                "limit": "5000",
            },
        )

    async def audit_logs(self) -> list[dict[str, Any]]:
        if self.client.settings.allow_mock_services:
            return []
        return await self.client.select(
            "admin_audit_logs", {"select": "*", "order": "created_at.desc", "limit": "500"}
        )

    async def audit(
        self,
        admin_id: str,
        action: str,
        target_type: str,
        target_id: str,
        before: Any = None,
        after: Any = None,
        request_id: str | None = None,
    ) -> None:
        if self.client.settings.allow_mock_services:
            return
        await self.client.insert(
            "admin_audit_logs",
            {
                "admin_id": admin_id,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "before_data": before,
                "after_data": after,
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def track(
        self, user_id: str | None, event_name: str, metadata: dict[str, Any] | None = None
    ) -> None:
        if self.client.settings.allow_mock_services:
            return
        await self.client.insert(
            "feature_usage_events", {"user_id": user_id, "event_name": event_name, "metadata": metadata or {}}
        )
