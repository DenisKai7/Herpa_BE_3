from datetime import datetime, timezone
from typing import Any
from app.core.constants import AccountStatus, ApplicationRole
from app.core.exceptions import NotFoundError
from app.models.profile import Profile
from app.services.supabase.client import SupabaseClient
from app.utils.cache import AsyncMemoryTTLCache


class ProfileService:
    def __init__(self, client: SupabaseClient):
        self.client = client
        self._mock: dict[str, dict[str, Any]] = {}
        self._cache = AsyncMemoryTTLCache(max_size=512)

    async def get(self, user_id: str, email: str = "") -> Profile:
        cache_key = f"profile:{user_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if self.client.settings.allow_mock_services:
            row = self._mock.get(user_id) or {
                "id": user_id,
                "email": email,
                "application_role": "user",
                "persona": "umum",
                "account_status": "active",
                "storage_quota_bytes": 104857600,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._mock[user_id] = row
            res = Profile.model_validate(row)
            self._cache.set(cache_key, res, ttl_seconds=30)
            return res

        rows = await self.client.select("profiles", {"select": "*", "id": f"eq.{user_id}", "limit": "1"})
        if not rows:
            raise NotFoundError("Profil pengguna belum tersedia.")
        row = rows[0]
        row.setdefault("email", email)
        res = Profile.model_validate(row)
        self._cache.set(cache_key, res, ttl_seconds=30)
        return res

    async def upsert_from_auth(self, user: dict[str, Any]) -> Profile:
        user_id = user["id"]
        self._cache.clear()
        meta = user.get("user_metadata") or {}
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            "id": user_id,
            "email": user.get("email", ""),
            "username": meta.get("username"),
            "full_name": meta.get("nama") or meta.get("full_name"),
            "instansi": meta.get("instansi", ""),
            "provinsi": meta.get("provinsi", ""),
            "kota": meta.get("kota", ""),
            "application_role": "user",
            "persona": "umum",
            "account_status": "active",
            "updated_at": now,
        }
        if self.client.settings.allow_mock_services:
            self._mock[user_id] = payload | {"created_at": now, "storage_quota_bytes": 104857600}
            return Profile.model_validate(self._mock[user_id])
        rows = await self.client.request(
            "POST",
            "profiles",
            params={"on_conflict": "id"},
            json=payload,
            prefer="resolution=merge-duplicates,return=representation",
        )
        return Profile.model_validate(rows[0])

    async def update(self, user_id: str, payload: dict[str, Any]) -> Profile:
        self._cache.clear()
        clean = {
            k: v
            for k, v in payload.items()
            if v is not None
            and k in {"username", "full_name", "instansi", "provinsi", "kota", "persona", "avatar_object_key"}
        }
        clean["updated_at"] = datetime.now(timezone.utc).isoformat()
        if self.client.settings.allow_mock_services:
            current = (await self.get(user_id)).model_dump()
            current.update(clean)
            self._mock[user_id] = current
            return Profile.model_validate(current)
        rows = await self.client.update("profiles", {"id": f"eq.{user_id}"}, clean)
        if not rows:
            raise NotFoundError("Profil tidak ditemukan.")
        return Profile.model_validate(rows[0])

    async def set_role(self, user_id: str, role: ApplicationRole | str) -> Profile:
        self._cache.clear()
        role_value = role.value if isinstance(role, ApplicationRole) else ApplicationRole(role).value
        if self.client.settings.allow_mock_services:
            current = (await self.get(user_id)).model_dump()
            current["application_role"] = role_value
            self._mock[user_id] = current
            return Profile.model_validate(current)
        rows = await self.client.update("profiles", {"id": f"eq.{user_id}"}, {"application_role": role_value})
        if not rows:
            raise NotFoundError("Pengguna tidak ditemukan.")
        return Profile.model_validate(rows[0])

    async def set_status(self, user_id: str, status: AccountStatus | str) -> Profile:
        self._cache.clear()
        status_value = status.value if isinstance(status, AccountStatus) else AccountStatus(status).value
        if self.client.settings.allow_mock_services:
            current = (await self.get(user_id)).model_dump()
            current["account_status"] = status_value
            self._mock[user_id] = current
            return Profile.model_validate(current)
        rows = await self.client.update("profiles", {"id": f"eq.{user_id}"}, {"account_status": status_value})
        if not rows:
            raise NotFoundError("Pengguna tidak ditemukan.")
        return Profile.model_validate(rows[0])
