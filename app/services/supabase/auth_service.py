from typing import Any
from app.core.exceptions import UnauthorizedError
from app.services.supabase.client import SupabaseClient
from app.utils.cache import AsyncMemoryTTLCache


class AuthService:
    def __init__(self, client: SupabaseClient):
        self.client = client
        self._cache = AsyncMemoryTTLCache(max_size=512)

    async def login(self, email: str, password: str) -> dict[str, Any]:
        return await self.client.auth_request(
            "POST", "token?grant_type=password", json={"email": email, "password": password}
        )

    async def register(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = payload["email"]
        password = payload["password"]
        metadata = {k: payload.get(k, "") for k in ("username", "nama", "instansi", "provinsi", "kota")}
        return await self.client.auth_request(
            "POST", "signup", json={"email": email, "password": password, "data": metadata}
        )

    async def verify_token_remote(self, token: str) -> dict[str, Any]:
        cached = self._cache.get(token)
        if cached is not None:
            return cached
        try:
            res = await self.client.auth_request("GET", "user", token=token)
            self._cache.set(token, res, ttl_seconds=30)
            return res
        except Exception as exc:
            raise UnauthorizedError("Token tidak valid atau sudah kedaluwarsa.") from exc

    async def change_password(self, token: str, new_password: str) -> None:
        self._cache.clear()
        await self.client.auth_request("PUT", "user", json={"password": new_password}, token=token)
