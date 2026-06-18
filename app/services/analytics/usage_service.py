from app.services.supabase.client import SupabaseClient


class UsageService:
    def __init__(self, client: SupabaseClient):
        self.client = client

    async def model_event(
        self,
        user_id: str | None,
        model: str,
        latency_ms: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        status: str = "success",
    ) -> None:
        if self.client.settings.allow_mock_services:
            return
        await self.client.insert(
            "model_usage_events",
            {
                "user_id": user_id,
                "model_name": model,
                "latency_ms": latency_ms,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "status": status,
            },
        )
