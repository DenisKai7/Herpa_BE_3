from app.services.supabase.quiz_service import QuizService


class QuizOrchestrator:
    def __init__(self, service: QuizService):
        self.service = service

    async def start(self, user_id: str, level_id: str, count: int):
        return await self.service.create_attempt(user_id, level_id, count)

    async def answer(self, user_id: str, attempt_id: str, payload: dict):
        return await self.service.answer(user_id, attempt_id, payload)

    async def complete(self, user_id: str, attempt_id: str):
        return await self.service.complete(user_id, attempt_id)
