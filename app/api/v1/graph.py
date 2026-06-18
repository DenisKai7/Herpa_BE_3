from fastapi import APIRouter, Depends, Query
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.models.auth import CurrentUser

router = APIRouter(prefix="/api/v1/graph", tags=["Knowledge Graph"])


@router.get("/search")
async def search(
    q: str = Query(min_length=2, max_length=200),
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    from app.graph.retriever import GraphRetriever

    return await GraphRetriever(services.graph_repository).retrieve(q)
