from app.core.exceptions import AppError


def validate_quota(current_bytes: int, incoming_bytes: int, quota_bytes: int) -> None:
    if current_bytes + incoming_bytes > quota_bytes:
        raise AppError("STORAGE_QUOTA_EXCEEDED", "Kuota penyimpanan pengguna tidak mencukupi.", 413)
