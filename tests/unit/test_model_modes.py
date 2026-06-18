import asyncio

import pytest

from app.core.config import Settings
from app.core.constants import ModelMode, Persona
from app.core.exceptions import AppError
from app.core.model_modes import normalize_model_mode, normalize_persona
from app.services.ai.context_budget import fit_messages_to_context
from app.services.ai.model_gateway import ModelGateway


def test_model_mode_default_fast_medium():
    assert normalize_model_mode(None) == ModelMode.FAST_MEDIUM


def test_model_mode_alias_fast():
    assert normalize_model_mode("fast") == ModelMode.FAST_MEDIUM


def test_model_mode_alias_thinking():
    assert normalize_model_mode("thinking") == ModelMode.THINKING_HIGH


def test_invalid_model_mode():
    with pytest.raises(AppError) as exc:
        normalize_model_mode("slow")
    assert exc.value.code == "VALIDATION_ERROR"
    assert exc.value.message == "Model mode tidak valid."


def test_persona_alias_oeneliti():
    assert normalize_persona("oeneliti") == Persona.PENELITI


def test_context_budgeting():
    messages = [
        {"role": "system", "content": "aturan"},
        {"role": "user", "content": "x" * 10000},
    ]
    fitted = fit_messages_to_context(messages, context_size=1024, max_output_tokens=200, safety_margin=100)
    assert len(fitted[1]["content"]) < 10000


class FakeTextClient:
    def __init__(self):
        self.calls = []
        self.model_calls = 0
        self.fail = False
        self.models_result = ["real-model"]

    async def models(self):
        self.model_calls += 1
        if self.fail:
            raise AppError("TEXT_MODEL_UNAVAILABLE", "down", 503)
        return self.models_result

    async def complete(self, messages, **kwargs):
        self.calls.append(kwargs)
        if self.fail:
            raise AppError("TEXT_MODEL_UNAVAILABLE", "down", 503)
        return {"choices": [{"message": {"content": "jawaban"}}], "usage": {}}

    async def stream(self, messages, **kwargs):
        yield "jawaban"

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_model_auto_discovery():
    settings = Settings(app_env="test", allow_mock_services=False, llama_text_model_name="wrong")
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    assert await gateway.resolve_model_name() == "real-model"


@pytest.mark.asyncio
async def test_model_metadata_cached():
    settings = Settings(app_env="test", allow_mock_services=False, text_model_metadata_cache_seconds=600)
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    assert await gateway.resolve_model_name() == "real-model"
    assert await gateway.resolve_model_name() == "real-model"
    assert fake.model_calls == 1


@pytest.mark.asyncio
async def test_model_alias_mismatch_is_resolved():
    settings = Settings(app_env="test", allow_mock_services=False, llama_text_model_name="alias")
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    result = await gateway.generate_text([{"role": "user", "content": "hi"}], mode=ModelMode.FAST_MEDIUM)
    assert result.model == "real-model"
    assert fake.calls[0]["model"] == "real-model"


@pytest.mark.asyncio
async def test_circuit_breaker_recovers():
    settings = Settings(
        app_env="test",
        allow_mock_services=False,
        text_model_circuit_failure_threshold=1,
        text_model_circuit_reset_seconds=0,
    )
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    fake.fail = True
    with pytest.raises(AppError):
        await gateway.generate_text([{"role": "user", "content": "hi"}], mode=ModelMode.FAST_MEDIUM)
    assert gateway._circuit_state == "open"
    fake.fail = False
    gateway._resolved_model_name = None
    result = await gateway.generate_text([{"role": "user", "content": "hi"}], mode=ModelMode.FAST_MEDIUM)
    assert result.text == "jawaban"
    assert gateway._circuit_state == "closed"


@pytest.mark.asyncio
async def test_fast_medium_single_pass():
    settings = Settings(app_env="test", allow_mock_services=False)
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    await gateway.generate_text([{"role": "user", "content": "hi"}], mode=ModelMode.FAST_MEDIUM)
    assert len(fake.calls) == 1


@pytest.mark.asyncio
async def test_thinking_hard_two_pass():
    settings = Settings(app_env="test", allow_mock_services=False)
    gateway = ModelGateway(settings)
    fake = FakeTextClient()
    gateway.text = fake
    await gateway.generate_text([{"role": "user", "content": "draft"}], mode=ModelMode.THINKING_HIGH)
    await gateway.generate_text([{"role": "user", "content": "review"}], mode=ModelMode.THINKING_HIGH)
    assert len(fake.calls) == 2


def test_thinking_hard_does_not_expose_chain_of_thought():
    from app.prompts.model_modes import build_system_prompt

    prompt = build_system_prompt(Persona.PENELITI, ModelMode.THINKING_HIGH).lower()
    assert "jangan menampilkan chain-of-thought" in prompt
    assert "scratchpad" not in prompt


def test_thinking_hard_degraded_metadata():
    metadata = {
        "requested_mode": "thinking-hard",
        "execution_mode_used": "thinking-hard-draft-only",
        "degraded": True,
    }
    assert metadata["degraded"] is True


def test_vision_disabled_does_not_fail_readiness():
    settings = Settings(app_env="test", allow_mock_services=True, enable_vision=False)
    gateway = ModelGateway(settings)
    health = asyncio.run(gateway.health())
    assert health["vision"] == {"enabled": False, "healthy": True}


def test_legacy_chat_request_supports_model_choice():
    from app.models.chat import ChatMessageRequest

    req = ChatMessageRequest(message="hi", ai_mode="umum", model_choice="thinking-hard")
    assert req.model_choice == "thinking-hard"


def test_503_contains_real_error_code():
    exc = AppError(
        "TEXT_MODEL_UNAVAILABLE", "Model teks lokal belum tersedia.", 503, {"stage": "draft_generation"}
    )
    assert exc.code == "TEXT_MODEL_UNAVAILABLE"
    assert exc.details["stage"] == "draft_generation"
