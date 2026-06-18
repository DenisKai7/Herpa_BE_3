import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)


class OpenAICompatibleClient:
    def __init__(self, base_url: str, model: str, timeout: float):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self.client.aclose()

    async def models(self) -> list[str]:
        try:
            response = await self.client.get(f"{self.base_url}/models", timeout=5)
        except httpx.TimeoutException as exc:
            raise AppError("TEXT_MODEL_TIMEOUT", "Model teks tidak merespons tepat waktu.", 503) from exc
        except httpx.HTTPError as exc:
            raise AppError("TEXT_MODEL_UNAVAILABLE", "Model teks lokal belum tersedia.", 503) from exc
        if response.status_code >= 500:
            self._log_http_error("models_failed", response)
            raise AppError("TEXT_MODEL_UNAVAILABLE", "Model teks lokal belum tersedia.", 503)
        if response.status_code >= 400:
            self._log_http_error("models_invalid", response)
            raise AppError("MODEL_OUTPUT_INVALID", "Respons daftar model tidak valid.", 502)
        try:
            data = response.json()
            return [str(item.get("id")) for item in data.get("data", []) if item.get("id")]
        except (ValueError, AttributeError) as exc:
            raise AppError("MODEL_OUTPUT_INVALID", "Respons daftar model tidak valid.", 502) from exc

    async def health(self) -> dict[str, Any]:
        try:
            models = await self.models()
        except AppError as exc:
            return {
                "healthy": False,
                "available_models": [],
                "last_error": exc.message,
                "error_code": exc.code,
            }
        return {"healthy": True, "available_models": models, "last_error": None, "error_code": None}

    async def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        payload = self._payload(messages, stream=False, **kwargs)
        attempts = 0
        removed_fields: set[str] = set()
        while True:
            attempts += 1
            try:
                response = await self.client.post(f"{self.base_url}/chat/completions", json=payload)
            except httpx.TimeoutException as exc:
                if attempts <= 2:
                    await asyncio.sleep(0.2 * attempts)
                    continue
                raise AppError("TEXT_MODEL_TIMEOUT", "Model teks tidak merespons tepat waktu.", 503) from exc
            except httpx.HTTPError as exc:
                if attempts <= 2:
                    await asyncio.sleep(0.2 * attempts)
                    continue
                raise AppError("TEXT_MODEL_UNAVAILABLE", "Model teks lokal belum tersedia.", 503) from exc

            if response.status_code == 400:
                response_body = response.text[:4000]
                normalized_body = response_body.lower()

                logger.warning(
                    "chat_bad_request",
                    extra={
                        "status_code": 400,
                        "response_body": response_body,
                        "model": payload.get("model"),
                        "message_count": len(payload.get("messages", [])),
                        "max_tokens": payload.get("max_tokens"),
                        "payload_fields": sorted(payload.keys()),
                    },
                )

                # Verify context errors
                context_markers = (
                    "context window",
                    "context size",
                    "n_ctx",
                    "too many tokens",
                    "prompt is too long",
                    "exceeds the context",
                    "maximum context",
                    "context overflow",
                    "requested tokens exceed",
                )
                is_context_error = any(marker in normalized_body for marker in context_markers)

                if is_context_error:
                    raise AppError(
                        code="MODEL_CONTEXT_OVERFLOW",
                        message="Prompt melebihi kapasitas konteks model.",
                        status_code=413,
                        details={
                            "response_body": response_body,
                            "model": payload.get("model"),
                            "message_count": len(payload.get("messages", [])),
                            "max_tokens": payload.get("max_tokens"),
                        },
                    )

                # Try parameter sanitization retry once
                unsupported_field = None
                for field_name in list(payload.keys()):
                    if field_name != "messages" and field_name in normalized_body:
                        unsupported_field = field_name
                        break

                if unsupported_field and unsupported_field not in removed_fields:
                    removed_fields.add(unsupported_field)
                    payload.pop(unsupported_field, None)
                    logger.warning(
                        "llama_payload_field_removed",
                        extra={
                            "removed_field": unsupported_field,
                            "remaining_fields": sorted(payload.keys()),
                        },
                    )
                    continue

                raise AppError(
                    code="MODEL_REQUEST_INVALID",
                    message="llama.cpp menolak format atau parameter request.",
                    status_code=502,
                    details={
                        "response_body": response_body,
                        "model": payload.get("model"),
                        "payload_fields": sorted(payload.keys()),
                    },
                )

            if response.status_code >= 500 and attempts <= 2:
                self._log_http_error("chat_retry", response)
                await asyncio.sleep(0.2 * attempts)
                continue
            if response.status_code >= 400:
                self._log_http_error("chat_failed", response)
                raise AppError("TEXT_MODEL_UNAVAILABLE", "Model teks gagal memproses permintaan.", 503)
            try:
                data = response.json()
                data["choices"][0]["message"]["content"]
                return data
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise AppError("MODEL_OUTPUT_INVALID", "Output model tidak valid.", 502) from exc

    async def stream(self, messages: list[dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        stream_metadata = kwargs.pop("stream_metadata", None)
        payload = self._payload(messages, stream=True, **kwargs)
        removed_fields: set[str] = set()
        while True:
            try:
                async with self.client.stream(
                    "POST", f"{self.base_url}/chat/completions", json=payload
                ) as response:
                    if response.status_code == 400:
                        response_body = (await response.aread()).decode("utf-8", errors="replace")[:4000]
                        normalized_body = response_body.lower()

                        logger.warning(
                            "stream_bad_request",
                            extra={
                                "status_code": 400,
                                "response_body": response_body,
                                "model": payload.get("model"),
                                "message_count": len(payload.get("messages", [])),
                                "payload_fields": sorted(payload.keys()),
                            },
                        )

                        context_markers = (
                            "context window",
                            "context size",
                            "n_ctx",
                            "too many tokens",
                            "prompt is too long",
                            "exceeds the context",
                            "maximum context",
                            "context overflow",
                            "requested tokens exceed",
                        )
                        is_context_error = any(marker in normalized_body for marker in context_markers)

                        if is_context_error:
                            raise AppError(
                                code="MODEL_CONTEXT_OVERFLOW",
                                message="Prompt melebihi kapasitas konteks model.",
                                status_code=413,
                                details={
                                    "response_body": response_body,
                                    "model": payload.get("model"),
                                },
                            )

                        unsupported_field = None
                        for field_name in list(payload.keys()):
                            if field_name != "messages" and field_name in normalized_body:
                                unsupported_field = field_name
                                break

                        if unsupported_field and unsupported_field not in removed_fields:
                            removed_fields.add(unsupported_field)
                            payload.pop(unsupported_field, None)
                            logger.warning(
                                "llama_payload_field_removed",
                                extra={
                                    "removed_field": unsupported_field,
                                    "remaining_fields": sorted(payload.keys()),
                                },
                            )
                            continue

                        raise AppError(
                            code="MODEL_REQUEST_INVALID",
                            message="Parameter request tidak didukung oleh llama.cpp.",
                            status_code=502,
                            details={
                                "response_body": response_body,
                                "model": payload.get("model"),
                            },
                        )

                    if response.status_code >= 400:
                        self._log_http_error("stream_failed", response)
                        raise AppError("TEXT_MODEL_UNAVAILABLE", "Streaming model gagal.", 503)

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw == "[DONE]":
                            break
                        try:
                            data = json.loads(raw)
                            choice = data["choices"][0]
                            if stream_metadata is not None and choice.get("finish_reason"):
                                stream_metadata["finish_reason"] = choice.get("finish_reason")
                            delta = choice.get("delta", {}).get("content")
                        except (ValueError, KeyError, IndexError, TypeError):
                            continue
                        if delta:
                            yield delta
                break
            except Exception as exc:
                if isinstance(exc, AppError):
                    raise
                raise AppError("TEXT_MODEL_UNAVAILABLE", "Streaming model tidak tersedia.", 503) from exc

    def _payload(self, messages: list[dict[str, Any]], stream: bool, **kwargs: Any) -> dict[str, Any]:
        payload = {
            "model": kwargs.get("model") or self.model,
            "messages": messages,
            "stream": stream,
            "temperature": kwargs.get("temperature", 0.2),
            "max_tokens": kwargs.get("max_tokens", 1200),
            "cache_prompt": True,
        }
        for key in ("top_p", "top_k", "min_p", "repeat_penalty"):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]
        return payload

    @staticmethod
    def _log_http_error(event: str, response: httpx.Response) -> None:
        logger.warning(
            event,
            extra={"status_code": response.status_code, "response_body": response.text[:500]},
        )
