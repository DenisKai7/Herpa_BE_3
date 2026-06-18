from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from app.api.dependencies.services import Services, get_services
from app.core.exceptions import NotFoundError
from app.core.security import hash_share_token

router = APIRouter(tags=["Shared Chats"])


@router.get("/api/chat/public/{share_id}")
@router.get("/api/v1/shared/{share_id}", include_in_schema=False)
async def public_chat(share_id: str, services: Services = Depends(get_services)):
    if services.settings.allow_mock_services:
        raise NotFoundError("Shared chat mock belum dibuat.")
    shares = await services.supabase.select(
        "shared_chats",
        {
            "select": "chat_id,expires_at",
            "share_token_hash": f"eq.{hash_share_token(share_id)}",
            "is_active": "eq.true",
            "limit": "1",
        },
    )
    if not shares:
        raise NotFoundError("Shared chat tidak ditemukan atau telah dicabut.")
    expires_at = shares[0].get("expires_at")
    if expires_at:
        parsed_expiry = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        if parsed_expiry <= datetime.now(timezone.utc):
            raise NotFoundError("Shared chat telah kedaluwarsa.")
    chat_id = shares[0]["chat_id"]
    chats = await services.supabase.select("chats", {"select": "title", "id": f"eq.{chat_id}", "limit": "1"})
    messages = await services.supabase.select(
        "chat_messages",
        {
            "select": "id,chat_id,role,content,metadata,quiz_data,file_context,created_at",
            "chat_id": f"eq.{chat_id}",
            "order": "created_at.asc",
        },
    )
    return {"title": chats[0]["title"] if chats else "Shared Chat", "messages": messages}
