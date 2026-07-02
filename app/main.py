import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.dependencies.services import close_services, create_services
from app.api.v1.router import router
from app.core.config import get_settings
from app.core.exceptions import AppError, app_error_handler
from app.core.logging import configure_logging
from app.core.telemetry import request_context_middleware

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = await create_services(settings)
    await app.state.services.storage.ensure_buckets()
    yield
    await close_services(app.state.services)


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)
app.middleware("http")(request_context_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    errors = exc.errors()
    logger.warning(
        "request_validation_failed",
        extra={
            "request_id": request_id,
            "path": str(request.url.path),
            "error_code": "VALIDATION_ERROR",
            "validation_errors": errors,
        },
    )
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Format request tidak sesuai.",
                "details": errors,
            },
            "meta": {"request_id": request_id},
        },
    )


app.include_router(router)

from app.evaluation.router import router as evaluation_router

app.include_router(evaluation_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "docs": "/docs", "health": "/api/v1/health/live"}
