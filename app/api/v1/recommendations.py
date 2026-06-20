import logging

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import Services, get_services
from app.core.json_safety import json_safe
from app.models.auth import CurrentUser
from app.models.recommendation import HerbalRecommendationRequest, HerbalRecommendationResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Herbal Recommendations"])


@router.post("/api/herbal-recommendations/analyze", response_model=HerbalRecommendationResponse)
@router.post("/api/v1/recommendations", response_model=HerbalRecommendationResponse, include_in_schema=False)
async def analyze(
    payload: HerbalRecommendationRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
) -> HerbalRecommendationResponse:
    return await services.recommendation_orchestrator.analyze(user.id, payload, request.state.request_id)


@router.get("/api/herbal-recommendations/herbs/{herb_id}/detail")
@router.get("/api/v1/recommendations/herbs/{herb_id}/detail", include_in_schema=False)
async def get_herb_recommendation_detail(
    herb_id: str,
    user: CurrentUser = Depends(get_current_user),
    services: Services = Depends(get_services),
):
    logger.info("herbal_detail_stage", extra={"stage": "detail_request_received", "herb_id": herb_id})
    detail = await services.recommendation_orchestrator.get_herb_recommendation_detail(herb_id, persona="umum")
    return json_safe(
        {
            "status": "completed",
            "herb_id": herb_id,
            "detail": detail,
            "disclaimer": "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan.",
        }
    )


@router.get("/api/v1/recommendations")
async def history(user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)):
    return await services.recommendation_orchestrator.history(user.id)


@router.get("/api/v1/recommendations/{session_id}")
async def get_recommendation(
    session_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
):
    return await services.recommendation_orchestrator.get(user.id, session_id)


@router.delete("/api/v1/recommendations/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recommendation(
    session_id: str, user: CurrentUser = Depends(get_current_user), services: Services = Depends(get_services)
) -> Response:
    await services.recommendation_orchestrator.delete(user.id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
