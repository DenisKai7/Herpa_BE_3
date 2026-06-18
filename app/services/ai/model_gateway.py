import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, TypeVar, Type

from pydantic import BaseModel

from app.core.config import Settings
from app.core.constants import ModelMode, Persona
from app.core.exceptions import AppError
from app.services.ai.model_modes import mode_profile
from app.services.ai.structured_output import parse_json_model
from app.services.ai.text_client import OpenAICompatibleClient
from app.services.ai.vision_client import VisionClient

T = TypeVar("T", bound=BaseModel)


@dataclass
class ModelResult:
    text: str
    model: str
    mode: ModelMode
    latency_ms: int
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None


class ModelGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.text = OpenAICompatibleClient(
            settings.llama_text_base_url,
            settings.llama_text_model_name,
            settings.text_model_timeout_seconds,
        )
        self.vision = VisionClient(
            settings.llama_vision_base_url,
            settings.llama_vision_model_name,
            settings.vision_model_timeout_seconds,
        )
        self._failures = 0
        self._lock = asyncio.Semaphore(1)
        self._circuit_state = "closed"
        self._opened_at: float | None = None
        self._last_error: str | None = None
        self._resolved_model_name: str | None = None
        self._resolved_at: float = 0.0
        self._available_models: list[str] = []

    async def close(self) -> None:
        await self.text.close()
        await self.vision.close()

    async def health(self) -> dict[str, Any]:
        text = await self._text_health()
        vision_healthy = True
        if self.settings.enable_vision and not self.settings.allow_mock_services:
            vision_healthy = bool((await self.vision.health()).get("healthy"))
        return {
            "text": text,
            "vision": {"enabled": self.settings.enable_vision, "healthy": vision_healthy},
        }

    async def resolve_model_name(self) -> str:
        cache_ttl = self.settings.text_model_metadata_cache_seconds
        if self._resolved_model_name and (time.monotonic() - self._resolved_at < cache_ttl):
            return self._resolved_model_name
        models = await self.text.models()
        self._available_models = models
        configured = self.settings.llama_text_model_name
        if configured in models:
            self._resolved_model_name = configured
            self._resolved_at = time.monotonic()
            return configured
        if self.settings.text_model_auto_discover and len(models) == 1:
            self._resolved_model_name = models[0]
            self._resolved_at = time.monotonic()
            return models[0]
        raise AppError(
            "TEXT_MODEL_UNAVAILABLE",
            "Model teks lokal belum tersedia.",
            503,
            {"configured_model": configured, "available_models": models, "service": "llama-text"},
        )

    async def generate_text(
        self,
        messages: list[dict[str, Any]],
        mode: ModelMode = ModelMode.FAST_MEDIUM,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ModelResult:
        if self.settings.allow_mock_services:
            text = (
                "Mode pengembangan aktif. Hubungkan llama.cpp untuk memperoleh jawaban model yang sebenarnya."
            )
            return ModelResult(text=text, model="mock", mode=mode, latency_ms=0, finish_reason="stop")
        await self._ensure_circuit_allows_request()
        async with self._lock:
            started = time.perf_counter()
            try:
                model_name = await self.resolve_model_name()
                data = await self.text.complete(
                    messages,
                    model=model_name,
                    **self._mode_params(mode, max_tokens=max_tokens),
                    **kwargs,
                )
                self._record_success()
                latency_ms = int((time.perf_counter() - started) * 1000)
                return ModelResult(
                    text=data["choices"][0]["message"]["content"],
                    model=model_name,
                    mode=mode,
                    latency_ms=latency_ms,
                    usage=data.get("usage", {}),
                    raw=data,
                    finish_reason=data.get("choices", [{}])[0].get("finish_reason"),
                )
            except AppError as exc:
                self._record_failure(exc)
                raise
            except Exception as exc:
                app_exc = AppError("TEXT_MODEL_UNAVAILABLE", "Model teks lokal belum tersedia.", 503)
                self._record_failure(app_exc)
                raise app_exc from exc

    async def stream_text(
        self,
        messages: list[dict[str, Any]],
        mode: ModelMode = ModelMode.FAST_MEDIUM,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        if self.settings.allow_mock_services:
            for (
                part
            ) in "Mode pengembangan aktif. Hubungkan llama.cpp untuk streaming jawaban sebenarnya.".split():
                yield part + " "
            return
        await self._ensure_circuit_allows_request()
        try:
            model_name = await self.resolve_model_name()
            async for token in self.text.stream(
                messages, model=model_name, **self._mode_params(mode), **kwargs
            ):
                yield token
            self._record_success()
        except AppError as exc:
            self._record_failure(exc)
            raise

    async def analyze_image(self, image_bytes: bytes, mime_type: str, prompt: str) -> str:
        if not self.settings.enable_vision:
            raise AppError("VISION_MODEL_UNAVAILABLE", "Model visual dinonaktifkan.", 503)
        if self.settings.allow_mock_services:
            return "Analisis gambar mock: model visual belum dihubungkan."
        data = await self.vision.analyze(image_bytes, mime_type, prompt)
        return data["choices"][0]["message"]["content"]

    async def generate_structured_output(self, messages: list[dict[str, Any]], schema: Type[T]) -> T:
        result = await self.generate_text(messages, mode=ModelMode.FAST_MEDIUM, temperature=0)
        return parse_json_model(result.text, schema)

    async def _text_health(self) -> dict[str, Any]:
        if self.settings.allow_mock_services:
            return {
                "healthy": True,
                "base_url": self.settings.llama_text_base_url,
                "configured_model": self.settings.llama_text_model_name,
                "resolved_model": "mock",
                "available_models": ["mock"],
                "circuit_state": self._circuit_state,
                "last_error": None,
            }
        model_name: str | None
        try:
            model_name = await self.resolve_model_name()
            self._record_success()
            healthy = True
        except AppError as exc:
            self._record_failure(exc)
            model_name = self._resolved_model_name
            healthy = False
        return {
            "healthy": healthy,
            "base_url": self.settings.llama_text_base_url,
            "configured_model": self.settings.llama_text_model_name,
            "resolved_model": model_name,
            "available_models": self._available_models,
            "circuit_state": self._circuit_state,
            "last_error": self._last_error,
        }

    async def _ensure_circuit_allows_request(self) -> None:
        if self._circuit_state != "open":
            return
        elapsed = time.monotonic() - (self._opened_at or 0)
        if elapsed < self.settings.text_model_circuit_reset_seconds:
            raise AppError("TEXT_MODEL_UNAVAILABLE", "Circuit breaker model sedang terbuka.", 503)
        self._circuit_state = "half-open"
        try:
            await self.resolve_model_name()
        except AppError as exc:
            self._record_failure(exc)
            raise AppError("TEXT_MODEL_UNAVAILABLE", "Circuit breaker model sedang terbuka.", 503) from exc
        self._record_success()

    def _record_success(self) -> None:
        self._failures = 0
        self._circuit_state = "closed"
        self._opened_at = None
        self._last_error = None

    def _record_failure(self, exc: AppError) -> None:
        self._failures += 1
        self._last_error = exc.message
        if self._failures >= self.settings.text_model_circuit_failure_threshold:
            self._circuit_state = "open"
            self._opened_at = time.monotonic()

    def _mode_params(
        self,
        mode: ModelMode,
        max_tokens: int | None = None,
        persona: Persona = Persona.UMUM,
    ) -> dict[str, Any]:
        profile = mode_profile(self.settings, mode, persona)
        return {
            "temperature": profile.temperature,
            "top_p": profile.top_p,
            "top_k": profile.top_k,
            "min_p": self.settings.thinking_high_min_p
            if mode == ModelMode.THINKING_HIGH
            else self.settings.fast_medium_min_p,
            "repeat_penalty": profile.repeat_penalty,
            "max_tokens": max_tokens or profile.max_output_tokens,
        }
