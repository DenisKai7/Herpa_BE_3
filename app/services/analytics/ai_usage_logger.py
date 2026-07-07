import logging
from typing import Any

from app.services.supabase.client import SupabaseClient

logger = logging.getLogger(__name__)


class AIUsageLogger:
    """Centralized AI usage logger for all AI features (Chat, Recommendation, Quiz, OCR)."""

    def __init__(self, client: SupabaseClient):
        self.client = client

    async def log(
        self,
        user_id: str | None,
        model: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        status: str = "success",
        error_code: str | None = None,
        persona: str | None = None,
        endpoint: str | None = None,
        provider: str = "local",
        prompt_text: str | None = None,
        response_text: str | None = None,
        retrieval_context: Any = None,
        request_id: str | None = None,
    ) -> None:
        """Log an AI usage event to model_usage_events table."""
        if self.client.settings.allow_mock_services:
            return

        try:
            await self.client.insert(
                "model_usage_events",
                {
                    "user_id": user_id,
                    "request_id": request_id,
                    "model_name": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "latency_ms": int(latency_ms),
                    "success": status == "success",
                    "error_code": error_code,
                    "persona": persona,
                    "endpoint": endpoint,
                    "provider": provider,
                    "prompt_text": prompt_text[:1000] if prompt_text else None,  # Truncate for storage
                    "response_text": response_text[:2000] if response_text else None,  # Truncate for storage
                    "retrieval_context": retrieval_context,
                },
            )
        except Exception as exc:
            logger.warning("ai_usage_log_failed", extra={"error": str(exc), "model": model})
