from pathlib import PurePath
from uuid import uuid4

import filetype

from app.core.config import Settings
from app.core.exceptions import AppError

ALLOWED = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "text/markdown",
    "text/csv",
}


def safe_filename(name: str) -> str:
    name = PurePath(name).name.replace(chr(0), "")
    return (
        "".join(character for character in name if character.isalnum() or character in "._- ")[:180] or "file"
    )


def validate_upload(
    data: bytes,
    filename: str,
    declared_type: str,
    settings: Settings,
) -> str:
    if len(data) > settings.max_upload_size_mb * 1024 * 1024:
        raise AppError(
            "ATTACHMENT_TOO_LARGE",
            "Ukuran attachment melebihi batas.",
            413,
        )
    detected = filetype.guess_mime(data) or (
        "text/plain" if declared_type.startswith("text/") else declared_type
    )
    if detected not in ALLOWED and declared_type not in ALLOWED:
        raise AppError(
            "UNSUPPORTED_FILE_TYPE",
            "Jenis berkas tidak didukung.",
            415,
            {"detected": detected},
        )
    return detected


def object_key(user_id: str, filename: str) -> str:
    extension = PurePath(filename).suffix.lower()[:12]
    return f"{user_id}/{uuid4()}{extension}"
