import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator

from app.agents.graph import AgenticGraph
from app.agents.state import AgentState
from app.core.exceptions import AppError
from app.core.model_modes import normalize_model_mode, normalize_persona
from app.models.chat import ChatMessageRequest, ChatResponse
from app.services.supabase.chat_service import ChatService

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    def __init__(self, chats: ChatService, agent_graph: AgenticGraph) -> None:
        self.chats = chats
        self.agent_graph = agent_graph

    async def process(
        self,
        user_id: str,
        request_id: str,
        payload: ChatMessageRequest,
        profile_persona: str,
        attachment_context: list[dict] | None = None,
    ) -> ChatResponse:
        started_all = time.perf_counter()
        persona = normalize_persona(payload.ai_mode or payload.persona, profile_persona)
        model_mode = normalize_model_mode(payload.model_choice)
        chat_id = payload.chat_id
        stage = "chat_persistence"
        try:
            started_persist = time.perf_counter()
            if chat_id is None:
                chat = await self.chats.create_chat(
                    user_id,
                    title=payload.message[:60] or "Percakapan Baru",
                    persona=persona.value,
                )
                chat_id = chat.id
            await self.chats.add_message(
                user_id,
                chat_id,
                "user",
                payload.message,
                metadata={
                    "ai_mode": persona.value,
                    "model_choice": model_mode.value,
                    "attachment_id": payload.attachment_id,
                },
                file_context=payload.file_context,
            )
            persist_user_ms = int((time.perf_counter() - started_persist) * 1000)

            stage = "draft_generation"
            state: AgentState = {
                "request_id": request_id,
                "user_id": user_id,
                "application_role": "user",
                "persona": persona.value,
                "model_mode": model_mode.value,
                "requested_mode": model_mode.value,
                "execution_mode_used": model_mode.value,
                "chat_id": chat_id,
                "user_query": payload.message,
                "attachment_ids": ([payload.attachment_id] if payload.attachment_id else [])
                + payload.attachment_ids,
                "attachment_context": attachment_context or [],
                "errors": [],
                "timings": {
                    "auth_ms": 0,
                    "profile_ms": 0,
                    "retrieval_ms": 0,
                    "ttft_ms": 0,
                    "generation_ms": 0,
                    "persistence_ms": 0,
                    "total_ms": 0,
                },
            }
            state = await self.agent_graph.run(state)
            if not state.get("grounded_answer"):
                raise AppError(
                    "MODEL_OUTPUT_INVALID",
                    "Model tidak menghasilkan jawaban valid.",
                    502,
                    {"stage": state.get("stage") or stage, "chat_id": chat_id},
                )

            stage = "assistant_persistence"
            started_persist_ai = time.perf_counter()
            # Calculate final timings
            timings = dict(state.get("timings") or {})
            timings["persistence_ms"] = (
                int((time.perf_counter() - started_persist_ai) * 1000) + persist_user_ms
            )
            timings["total_ms"] = int((time.perf_counter() - started_all) * 1000)

            message = await self.chats.add_message(
                user_id,
                chat_id,
                "ai",
                state.get("grounded_answer", "") or "",
                metadata={
                    "mode": model_mode.value,
                    "requested_mode": model_mode.value,
                    "execution_mode_used": state.get("execution_mode_used", model_mode.value),
                    "intent": state.get("query_intent") or state.get("intent"),
                    "legacy_intent": state.get("intent"),
                    "direct_answer_used": state.get("direct_answer_used", False),
                    "model_calls": state.get("model_calls", state.get("model_call_count", 0)),
                    "refinement_used": state.get("refinement_used", False),
                    "compound_count": state.get("compound_count", 0),
                    "retrieval_source": state.get("retrieval_source"),
                    "finish_reason": state.get("finish_reason"),
                    "tools_used": state.get("tools_used", []),
                    "retrieval_count": state.get("retrieval_count", 0),
                    "grounding_status": state.get("grounding_status"),
                    "confidence": state.get("confidence"),
                    "latency": state.get("latency_ms"),
                    "error_code": state.get("error_code"),
                    "sources": state.get("citations", []),
                    "degraded": state.get("degraded", False),
                    "timings": timings,
                },
            )
            response = ChatResponse(
                chat_id=chat_id,
                response=message.content,
                message=message,
                persona=state.get("persona"),
                model_choice=model_mode.value,
                execution_mode_used=state.get("execution_mode_used", model_mode.value),
                degraded=state.get("degraded", False),
                intent=state.get("intent"),
                confidence=state.get("confidence"),
                grounding_status=state.get("grounding_status"),
                sources=state.get("citations", []),
                warnings=state.get("warnings", []),
                latency_ms=state.get("latency_ms"),
            )
            return response
        except AppError as exc:
            exc.details.setdefault("stage", exc.details.get("stage") or stage)
            exc.details.setdefault(
                "service", "llama-text" if exc.code.startswith(("TEXT_MODEL", "MODEL_")) else "backend"
            )
            if chat_id:
                exc.details.setdefault("chat_id", chat_id)
            logger.warning(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "chat_id": chat_id,
                    "persona": persona.value,
                    "model_mode": model_mode.value,
                    "stage": exc.details.get("stage"),
                    "error_code": exc.code,
                },
            )
            raise

    async def stream(
        self,
        user_id: str,
        request_id: str,
        payload: ChatMessageRequest,
        profile_persona: str,
        attachment_context: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        started_all = time.perf_counter()
        persona = normalize_persona(payload.ai_mode or payload.persona, profile_persona)
        model_mode = normalize_model_mode(payload.model_choice)
        chat_id = payload.chat_id

        yield self._event(
            "message.started",
            {"request_id": request_id, "model_choice": model_mode.value, "persona": persona.value},
        )

        started_persist = time.perf_counter()
        if chat_id is None:
            chat = await self.chats.create_chat(
                user_id,
                title=payload.message[:60] or "Percakapan Baru",
                persona=persona.value,
            )
            chat_id = chat.id
        await self.chats.add_message(
            user_id,
            chat_id,
            "user",
            payload.message,
            metadata={
                "ai_mode": persona.value,
                "model_choice": model_mode.value,
                "attachment_id": payload.attachment_id,
            },
            file_context=payload.file_context,
        )
        persist_user_ms = int((time.perf_counter() - started_persist) * 1000)

        state: AgentState = {
            "request_id": request_id,
            "user_id": user_id,
            "application_role": "user",
            "persona": persona.value,
            "model_mode": model_mode.value,
            "requested_mode": model_mode.value,
            "execution_mode_used": model_mode.value,
            "chat_id": chat_id,
            "user_query": payload.message,
            "attachment_ids": ([payload.attachment_id] if payload.attachment_id else [])
            + payload.attachment_ids,
            "attachment_context": attachment_context or [],
            "errors": [],
            "timings": {
                "auth_ms": 0,
                "profile_ms": 0,
                "retrieval_ms": 0,
                "ttft_ms": 0,
                "generation_ms": 0,
                "persistence_ms": 0,
                "total_ms": 0,
            },
        }

        # Create queue for real-time tokens/events from graph
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(self.agent_graph.run(state, queue))

        tokens = []
        try:
            while not (task.done() and queue.empty()):
                try:
                    name, data = await asyncio.wait_for(queue.get(), timeout=0.05)
                    if name == "token" and data.get("text"):
                        tokens.append(str(data["text"]))
                    yield self._event(name, data)
                    queue.task_done()
                except asyncio.TimeoutError:
                    continue

            # Check if task raised exceptions
            exc = task.exception()
            if exc:
                raise exc

            final_state = await task
            final_text = "".join(tokens) or str(final_state.get("grounded_answer") or "")

            started_persist_ai = time.perf_counter()
            timings = dict(final_state.get("timings") or {})
            timings["persistence_ms"] = (
                int((time.perf_counter() - started_persist_ai) * 1000) + persist_user_ms
            )
            timings["total_ms"] = int((time.perf_counter() - started_all) * 1000)

            # Persist response once at completion
            await self.chats.add_message(
                user_id,
                chat_id,
                "ai",
                final_text,
                metadata={
                    "mode": model_mode.value,
                    "requested_mode": model_mode.value,
                    "execution_mode_used": final_state.get("execution_mode_used", model_mode.value),
                    "intent": final_state.get("intent"),
                    "tools_used": final_state.get("tools_used", []),
                    "retrieval_count": final_state.get("retrieval_count", 0),
                    "grounding_status": final_state.get("grounding_status"),
                    "confidence": final_state.get("confidence"),
                    "latency": final_state.get("latency_ms"),
                    "error_code": final_state.get("error_code"),
                    "sources": final_state.get("citations", []),
                    "degraded": final_state.get("degraded", False),
                    "timings": timings,
                },
            )

            yield self._event(
                "message.completed",
                {
                    "chat_id": chat_id,
                    "response": final_text,
                    "model_choice": model_mode.value,
                    "execution_mode_used": final_state.get("execution_mode_used", model_mode.value),
                    "persona": final_state.get("persona"),
                    "grounding_status": final_state.get("grounding_status"),
                    "degraded": final_state.get("degraded", False),
                    "timings": timings,
                },
            )
        except AppError as exc:
            yield self._event(
                "message.failed", {"code": exc.code, "message": exc.message, "details": exc.details}
            )
            raise
        except Exception as exc:
            yield self._event("message.failed", {"code": "INTERNAL_SERVER_ERROR", "message": str(exc)})
            raise exc

    @staticmethod
    def _event(name: str, data: dict) -> str:
        return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
