from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from app.core.exceptions import NotFoundError
from app.models.chat import ChatMessage, ChatSession
from app.services.supabase.client import SupabaseClient


class ChatService:
    def __init__(self, client: SupabaseClient):
        self.client = client
        self._chats: dict[str, dict[str, Any]] = {}
        self._messages: dict[str, list[dict[str, Any]]] = {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def create_chat(
        self, user_id: str, title: str = "Percakapan Baru", persona: str = "umum"
    ) -> ChatSession:
        now = self._now()
        row: dict[str, Any] = {
            "id": str(uuid4()),
            "user_id": user_id,
            "title": title,
            "is_pinned": False,
            "is_public": False,
            "is_archived": False,
            "persona_snapshot": persona,
            "created_at": now,
            "updated_at": now,
            "last_message_at": None,
        }
        if self.client.settings.allow_mock_services:
            self._chats[row["id"]] = row
            return ChatSession.model_validate(row)
        rows = await self.client.insert("chats", row)
        return ChatSession.model_validate(rows[0])

    async def list_chats(self, user_id: str, search: str | None = None) -> list[ChatSession]:
        if self.client.settings.allow_mock_services:
            rows = [r for r in self._chats.values() if r["user_id"] == user_id and not r.get("deleted_at")]
            if search:
                rows = [r for r in rows if search.lower() in r["title"].lower()]
        else:
            params = {
                "select": "*",
                "user_id": f"eq.{user_id}",
                "deleted_at": "is.null",
                "order": "is_pinned.desc,last_message_at.desc.nullslast,updated_at.desc",
            }
            if search:
                params["title"] = f"ilike.*{search}*"
            rows = await self.client.select("chats", params)
        return [ChatSession.model_validate(r) for r in rows]

    async def get_chat(self, user_id: str, chat_id: str) -> ChatSession:
        if self.client.settings.allow_mock_services:
            row = self._chats.get(chat_id)
            if not row or row["user_id"] != user_id:
                raise NotFoundError("Chat tidak ditemukan.")
        else:
            rows = await self.client.select(
                "chats", {"select": "*", "id": f"eq.{chat_id}", "user_id": f"eq.{user_id}", "limit": "1"}
            )
            if not rows:
                raise NotFoundError("Chat tidak ditemukan.")
            row = rows[0]
        return ChatSession.model_validate(row)

    async def update_chat(self, user_id: str, chat_id: str, payload: dict[str, Any]) -> ChatSession:
        await self.get_chat(user_id, chat_id)
        payload = {k: v for k, v in payload.items() if v is not None}
        payload["updated_at"] = self._now()
        if self.client.settings.allow_mock_services:
            self._chats[chat_id].update(payload)
            row = self._chats[chat_id]
        else:
            rows = await self.client.update(
                "chats", {"id": f"eq.{chat_id}", "user_id": f"eq.{user_id}"}, payload
            )
            row = rows[0]
        return ChatSession.model_validate(row)

    async def delete_chat(self, user_id: str, chat_id: str) -> None:
        await self.get_chat(user_id, chat_id)
        if self.client.settings.allow_mock_services:
            self._chats[chat_id]["deleted_at"] = self._now()
        else:
            await self.client.update(
                "chats", {"id": f"eq.{chat_id}", "user_id": f"eq.{user_id}"}, {"deleted_at": self._now()}
            )

    async def add_message(
        self, user_id: str, chat_id: str, role: str, content: str, **extra: Any
    ) -> ChatMessage:
        await self.get_chat(user_id, chat_id)
        now = self._now()
        row: dict[str, Any] = {
            "id": str(uuid4()),
            "chat_id": chat_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": extra.get("metadata"),
            "quiz_data": extra.get("quiz_data"),
            "file_context": extra.get("file_context"),
            "created_at": now,
        }
        if self.client.settings.allow_mock_services:
            self._messages.setdefault(chat_id, []).append(row)
        else:
            rows = await self.client.insert("chat_messages", row)
            row = rows[0]
        await self.update_chat(user_id, chat_id, {"last_message_at": now})
        return ChatMessage.model_validate(row)

    async def list_messages(self, user_id: str, chat_id: str) -> list[ChatMessage]:
        await self.get_chat(user_id, chat_id)
        rows = (
            self._messages.get(chat_id, [])
            if self.client.settings.allow_mock_services
            else await self.client.select(
                "chat_messages", {"select": "*", "chat_id": f"eq.{chat_id}", "order": "created_at.asc"}
            )
        )
        return [ChatMessage.model_validate(r) for r in rows]
