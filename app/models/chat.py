from typing import Any
from pydantic import BaseModel, Field
from app.core.constants import Persona, ModelMode
from app.models.common import SourceReference


class ChatCreate(BaseModel):
    title: str = Field(default="Percakapan Baru", max_length=160)
    persona: Persona | None = None


class ChatUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    is_archived: bool | None = None
    is_pinned: bool | None = None


class ChatSession(BaseModel):
    id: str
    title: str
    is_pinned: bool = False
    is_public: bool = False
    is_archived: bool = False
    created_at: str
    updated_at: str
    last_message_at: str | None = None


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    ai_mode: str | None = None
    persona: str | None = None
    chat_id: str | None = None
    attachment_id: str | None = None
    attachment_ids: list[str] = Field(default_factory=list)
    file_context: str | None = None
    file_url: str | None = None
    file_name: str | None = None
    file_type: str | None = None
    model_choice: str = ModelMode.FAST_MEDIUM.value


class ChatMessage(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    metadata: dict[str, Any] | None = None
    quiz_data: dict[str, Any] | None = None
    file_context: str | None = None
    created_at: str
    sources: list[SourceReference] = Field(default_factory=list)


class ChatResponse(BaseModel):
    chat_id: str
    response: str
    quiz_data: dict[str, Any] | None = None
    message: ChatMessage | None = None
    persona: str | None = None
    model_choice: str | None = None
    execution_mode_used: str | None = None
    degraded: bool = False
    intent: str | None = None
    confidence: float | None = None
    grounding_status: str | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    latency_ms: int | None = None


class RenameChatRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)


class PinChatRequest(BaseModel):
    is_pinned: bool


class ShareChatRequest(BaseModel):
    is_public: bool = True


class ShareChatResponse(BaseModel):
    share_id: str
    is_public: bool
    public_url: str | None = None
