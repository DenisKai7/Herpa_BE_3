from fastapi import APIRouter
from app.api.v1 import (
    admin,
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
    storage.router,
    shared_chats.router,
    health.router,
]:
    router.include_router(child)
