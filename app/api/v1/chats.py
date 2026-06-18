from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.core.rate_limit import rate_limiter
from app.models.auth import CurrentUser
from app.models.chat import (
    ChatCreate,
    ChatMessageRequest,
    ChatSession,
    PinChatRequest,
    RenameChatRequest,
    ShareChatRequest,
    ShareChatResponse,
)

router = APIRouter(tags=["Chats"])


@router.get("/api/chat/list")
@router.get("/api/v1/chats", include_in_schema=False)
async def list_chats(
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
    search: str | None = Query(default=None),
):
    return {"chats": [x.model_dump(mode="json") for x in await services.chats.list_chats(user.id, search)]}


@router.post("/api/v1/chats", response_model=ChatSession)
async def create_chat(
    payload: ChatCreate,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatSession:
    return await services.chats.create_chat(user.id, payload.title, (payload.persona or user.persona).value)


@router.get("/api/chat/{chat_id}/messages")
@router.get("/api/v1/chats/{chat_id}/messages", include_in_schema=False)
async def messages(
    chat_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return {
        "messages": [x.model_dump(mode="json") for x in await services.chats.list_messages(user.id, chat_id)]
    }


@router.get("/api/v1/chats/{chat_id}", response_model=ChatSession)
async def get_chat(
    chat_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> ChatSession:
    return await services.chats.get_chat(user.id, chat_id)


@router.patch("/api/chat/{chat_id}/rename", response_model=ChatSession)
async def rename(
    chat_id: str,
    payload: RenameChatRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatSession:
    return await services.chats.update_chat(user.id, chat_id, {"title": payload.title})


@router.patch("/api/chat/{chat_id}/pin", response_model=ChatSession)
async def pin_legacy(
    chat_id: str,
    payload: PinChatRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatSession:
    return await services.chats.update_chat(user.id, chat_id, {"is_pinned": payload.is_pinned})


@router.post("/api/v1/chats/{chat_id}/pin", response_model=ChatSession)
async def pin(
    chat_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> ChatSession:
    return await services.chats.update_chat(user.id, chat_id, {"is_pinned": True})


@router.delete("/api/v1/chats/{chat_id}/pin", response_model=ChatSession)
async def unpin(
    chat_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> ChatSession:
    return await services.chats.update_chat(user.id, chat_id, {"is_pinned": False})


@router.patch("/api/v1/chats/{chat_id}", response_model=ChatSession)
async def update_chat(
    chat_id: str,
    payload: RenameChatRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ChatSession:
    return await services.chats.update_chat(user.id, chat_id, {"title": payload.title})


@router.delete("/api/chat/{chat_id}", status_code=204)
@router.delete("/api/v1/chats/{chat_id}", status_code=204, include_in_schema=False)
async def delete_chat(
    chat_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> None:
    await services.chats.delete_chat(user.id, chat_id)


@router.post("/api/chat/message")
@router.post("/api/v1/chats/messages", include_in_schema=False)
async def send_message(
    payload: ChatMessageRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> dict:
    rate_limiter.check(f"chat:{user.id}", services.settings.rate_limit_chat_per_minute)
    ids = ([payload.attachment_id] if payload.attachment_id else []) + payload.attachment_ids
    context = await services.attachments.context(user.id, ids) if ids else []
    result = await services.chat_orchestrator.process(
        user.id, request.state.request_id, payload, user.persona.value, context
    )
    data = {
        "chat_id": result.chat_id,
        "message_id": result.message.id if result.message else None,
        "answer": result.response,
        "persona": result.persona,
        "model_choice": result.model_choice,
        "execution_mode_used": result.execution_mode_used,
        "degraded": result.degraded,
        "grounding_status": result.grounding_status,
        "confidence": result.confidence,
        "sources": [source.model_dump() for source in result.sources],
        "warnings": result.warnings,
        "latency_ms": result.latency_ms,
    }
    return {
        "success": True,
        "data": data,
        "meta": {"request_id": request.state.request_id},
        **data,
        "response": result.response,
    }


@router.post("/api/chat/message/stream")
@router.post("/api/v1/chats/messages/stream", include_in_schema=False)
@router.post("/api/v1/chats/{chat_id}/messages/stream", include_in_schema=False)
async def stream_message(
    payload: ChatMessageRequest,
    request: Request,
    chat_id: str | None = None,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> StreamingResponse:
    rate_limiter.check(f"chat:{user.id}", services.settings.rate_limit_chat_per_minute)
    if chat_id and not payload.chat_id:
        payload.chat_id = chat_id
    ids = ([payload.attachment_id] if payload.attachment_id else []) + payload.attachment_ids
    context = await services.attachments.context(user.id, ids) if ids else []
    return StreamingResponse(
        services.chat_orchestrator.stream(
            user.id, request.state.request_id, payload, user.persona.value, context
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.patch("/api/chat/{chat_id}/share", response_model=ShareChatResponse)
@router.post("/api/v1/chats/{chat_id}/share", response_model=ShareChatResponse, include_in_schema=False)
async def share(
    chat_id: str,
    payload: ShareChatRequest,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ShareChatResponse:
    from app.core.security import generate_share_token, hash_share_token, share_expiry

    # Ownership is checked by update_chat before share state is changed.
    token = generate_share_token() if payload.is_public else ""
    await services.chats.update_chat(user.id, chat_id, {"is_public": payload.is_public})
    if not services.settings.allow_mock_services:
        if payload.is_public:
            # Revoke older links so only the newest token remains valid.
            await services.supabase.update(
                "shared_chats",
                {"chat_id": f"eq.{chat_id}", "owner_id": f"eq.{user.id}"},
                {"is_active": False},
            )
            await services.supabase.insert(
                "shared_chats",
                {
                    "chat_id": chat_id,
                    "owner_id": user.id,
                    "share_token_hash": hash_share_token(token),
                    "is_active": True,
                    "expires_at": share_expiry(services.settings.share_token_expiry_days),
                },
            )
        else:
            await services.supabase.update(
                "shared_chats",
                {"chat_id": f"eq.{chat_id}", "owner_id": f"eq.{user.id}"},
                {"is_active": False},
            )
    return ShareChatResponse(
        share_id=token, is_public=payload.is_public, public_url=f"/share/{token}" if token else None
    )


@router.delete("/api/v1/chats/{chat_id}/share", response_model=ShareChatResponse)
async def revoke_share(
    chat_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> ShareChatResponse:
    return await share(chat_id, ShareChatRequest(is_public=False), user, services)
