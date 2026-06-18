from typing import Literal
from pydantic import BaseModel, Field

AttachmentStatus = Literal["uploading", "queued", "processing", "completed", "failed"]


class PresignUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    size_bytes: int = Field(gt=0)
    purpose: Literal["chat", "avatar"] = "chat"


class PresignUploadResponse(BaseModel):
    attachment_id: str
    object_key: str
    upload_url: str
    expires_in: int


class AttachmentCompleteRequest(BaseModel):
    object_key: str
    filename: str
    content_type: str
    size_bytes: int


class AttachmentInfo(BaseModel):
    id: str
    filename: str
    stored_filename: str | None = None
    mime_type: str | None = None
    preview_url: str | None = None
    processing_status: AttachmentStatus = "queued"
    detected_type: str | None = None
    verification_status: str = "pending"
    confidence: float = 0.0


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    extracted_text: str = ""
    content_type: str
    url: str | None = None
    success: bool = True
    attachment: AttachmentInfo
    context: dict = Field(default_factory=dict)


class AttachmentStatusResponse(BaseModel):
    attachment_id: str
    processing_status: AttachmentStatus
    progress: int = Field(ge=0, le=100)
    verification_status: str
    confidence: float
    extracted_text: str | None = None
    detected_type: str | None = None
    retryable: bool = False
    error: dict | None = None
