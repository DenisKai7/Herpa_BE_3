from typing import Any
import httpx
from app.core.config import Settings
from app.core.exceptions import AppError


class SupabaseClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = settings.supabase_url.rstrip("/")
        self.rest_url = f"{self.base_url}/rest/v1"
        self.auth_url = f"{self.base_url}/auth/v1"
        self._client = httpx.AsyncClient(timeout=30.0)

    @property
    def service_headers(self) -> dict[str, str]:
        key = self.settings.supabase_service_role_key
        return {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    async def close(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        if self.settings.allow_mock_services:
            return True
        try:
            response = await self._client.get(
                f"{self.rest_url}/profiles",
                params={"select": "id", "limit": "1"},
                headers=self.service_headers,
            )
            return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def request(
        self,
        method: str,
        table: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        prefer: str | None = "return=representation",
    ) -> Any:
        if self.settings.allow_mock_services:
            return []
        headers = dict(self.service_headers)
        if prefer:
            headers["Prefer"] = prefer
        try:
            response = await self._client.request(
                method, f"{self.rest_url}/{table}", params=params, json=json, headers=headers
            )
        except httpx.HTTPError as exc:
            raise AppError("SUPABASE_UNAVAILABLE", "Supabase tidak dapat dihubungi.", 503) from exc
        if response.status_code >= 400:
            raise AppError(
                "SUPABASE_ERROR",
                "Operasi database gagal.",
                response.status_code,
                {"response": response.text[:500]},
            )
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    async def select(self, table: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        result = await self.request("GET", table, params=params, prefer=None)
        return result if isinstance(result, list) else []

    async def select_with_count(
        self, table: str, params: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], int]:
        """SELECT with Prefer: count=exact. Returns (rows, total_count)."""
        if self.settings.allow_mock_services:
            return [], 0
        headers = dict(self.service_headers)
        headers["Prefer"] = "count=exact"
        try:
            response = await self._client.request(
                "GET", f"{self.rest_url}/{table}", params=params, headers=headers
            )
        except httpx.HTTPError as exc:
            raise AppError("SUPABASE_UNAVAILABLE", "Supabase tidak dapat dihubungi.", 503) from exc
        if response.status_code >= 400:
            raise AppError(
                "SUPABASE_ERROR", "Operasi database gagal.",
                response.status_code, {"response": response.text[:500]},
            )
        rows = response.json() if response.content else []
        if not isinstance(rows, list):
            rows = []
        total = 0
        content_range = response.headers.get("content-range", "")
        if "/" in content_range:
            try:
                total = int(content_range.rsplit("/", 1)[1])
            except (ValueError, IndexError):
                total = len(rows)
        else:
            total = len(rows)
        return rows, total

    async def insert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]]) -> Any:
        return await self.request("POST", table, json=payload)

    async def upsert(self, table: str, payload: dict[str, Any] | list[dict[str, Any]], on_conflict: str = "id") -> Any:
        """Insert or update on conflict. Uses PostgREST resolution=merge-duplicates."""
        return await self.request("POST", table, json=payload, prefer="return=representation,resolution=merge-duplicates")

    async def update(self, table: str, params: dict[str, Any], payload: dict[str, Any]) -> Any:
        return await self.request("PATCH", table, params=params, json=payload)

    async def delete(self, table: str, params: dict[str, Any]) -> None:
        await self.request("DELETE", table, params=params, prefer="return=minimal")

    async def auth_request(
        self, method: str, path: str, *, json: Any = None, token: str | None = None
    ) -> Any:
        headers = {
            "apikey": self.settings.supabase_publishable_key or self.settings.supabase_service_role_key,
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = await self._client.request(
            method, f"{self.auth_url}/{path.lstrip('/')}", headers=headers, json=json
        )
        if response.status_code >= 400:
            message = "Autentikasi Supabase gagal."
            try:
                body = response.json()
                message = body.get("msg") or body.get("message") or message
            except Exception:
                pass
            raise AppError("AUTH_ERROR", message, response.status_code)
        return response.json() if response.content else None

    async def auth_admin_request(
        self, method: str, path: str, *, json: Any = None
    ) -> Any:
        """Auth request using service_role_key (admin-level access)."""
        key = self.settings.supabase_service_role_key
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        response = await self._client.request(
            method, f"{self.auth_url}/{path.lstrip('/')}", headers=headers, json=json
        )
        if response.status_code >= 400:
            message = "Operasi admin Supabase gagal."
            try:
                body = response.json()
                message = body.get("msg") or body.get("message") or message
            except Exception:
                pass
            raise AppError("AUTH_ADMIN_ERROR", message, response.status_code)
        return response.json() if response.content else None
