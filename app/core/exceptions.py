from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    def __init__(
        self, code: str, message: str, status_code: int = 400, details: dict[str, Any] | None = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Autentikasi diperlukan."):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Anda tidak memiliki izin."):
        super().__init__("FORBIDDEN", message, 403)


class BadRequestError(AppError):
    def __init__(self, message: str = "Permintaan tidak valid."):
        super().__init__("BAD_REQUEST", message, 400)


class NotFoundError(AppError):
    def __init__(self, message: str = "Data tidak ditemukan."):
        super().__init__("RESOURCE_NOT_FOUND", message, 404)


class ConflictError(AppError):
    def __init__(self, message: str = "Data konflik.", code: str = "CONFLICT", details: dict[str, Any] | None = None):
        super().__init__(code, message, 409, details)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            "detail": {
                "code": exc.code,
                "message": exc.message,
                "error": {"code": exc.code, "message": exc.message},
            },
            "meta": {"request_id": request_id},
        },
    )
