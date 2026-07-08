from fastapi import APIRouter
from app.api.v1 import (
    admin,
    admin_graphrag,
    admin_quiz,
    admin_recommendations,
    ai_usage,
    attachments,
    auth,
    chats,
    graph,
    health,
    profiles,
    quiz,
    recommendations,
    shared_chats,
    storage,
)

router = APIRouter()
for child in [
    auth.router,
    profiles.router,
    chats.router,
    attachments.router,
    recommendations.router,
    quiz.router,
    graph.router,
    admin.router,
    admin_graphrag.router,
    admin_quiz.router,
    admin_recommendations.router,
    ai_usage.router,
    storage.router,
    shared_chats.router,
    health.router,
]:
    router.include_router(child)
