from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies.services import Services, get_services

router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response, services: Services = Depends(get_services)):
    model_health = await services.model_gateway.health()
    deps = {
        "supabase": await services.supabase.health(),
        "neo4j": await services.neo4j.health(),
        "minio": await services.storage.health(),
        "text_model": bool(model_health["text"].get("healthy")),
        "vision": True
        if not model_health["vision"].get("enabled")
        else bool(model_health["vision"].get("healthy")),
    }
    ok = all(deps.values())
    if not ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ok else "degraded", "dependencies": deps}


@router.get("/dependencies")
async def dependencies(services: Services = Depends(get_services)):
    neo4j_healthy = await services.neo4j.health()
    fulltext_status = {"exists": False, "state": "UNKNOWN"}
    if neo4j_healthy and not services.settings.allow_mock_services:
        fulltext_status = await services.graph_repository.fulltext_index_status("herb_fulltext_idx")
    return {
        "supabase": await services.supabase.health(),
        "neo4j": neo4j_healthy,
        "neo4j_fulltext_index": fulltext_status,
        "minio": await services.storage.health(),
        "models": await services.model_gateway.health(),
    }


@router.get("/neo4j")
async def neo4j_health(services: Services = Depends(get_services)):
    healthy = await services.neo4j.health()
    status = {"exists": False, "state": "UNKNOWN"}
    if healthy and not services.settings.allow_mock_services:
        status = await services.graph_repository.fulltext_index_status("herb_fulltext_idx")
    return {"healthy": healthy, "fulltext_index": status}


@router.get("/models")
async def models(services: Services = Depends(get_services)):
    return await services.model_gateway.health()
