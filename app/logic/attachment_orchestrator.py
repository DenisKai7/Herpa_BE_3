from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.models.attachment import (
    AttachmentCompleteRequest,
    AttachmentInfo,
    AttachmentStatusResponse,
    FileUploadResponse,
    PresignUploadRequest,
    PresignUploadResponse,
)
from app.services.documents.extractor import DocumentExtractor
from app.services.documents.image_processor import ImageProcessor
from app.services.storage.minio_client import MinioStorage
from app.services.storage.storage_quota import validate_quota
from app.services.storage.upload_service import ALLOWED, object_key, safe_filename, validate_upload
from app.services.supabase.client import SupabaseClient


class AttachmentOrchestrator:
    def __init__(
        self,
        settings: Settings,
        storage: MinioStorage,
        db: SupabaseClient,
        extractor: DocumentExtractor,
        image: ImageProcessor,
    ):
        self.settings = settings
        self.storage = storage
        self.db = db
        self.extractor = extractor
        self.image = image
        self._mock: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _usage(self, user_id: str) -> int:
        if self.db.settings.allow_mock_services:
            return sum(
                int(row.get("size_bytes", 0))
                for row in self._mock.values()
                if row["user_id"] == user_id and not row.get("deleted_at")
            )
        rows = await self.db.select(
            "storage_objects", {"select": "size_bytes", "user_id": f"eq.{user_id}", "deleted_at": "is.null"}
        )
        return sum(int(row.get("size_bytes", 0)) for row in rows)

    async def _quota(self, user_id: str) -> int:
        if self.db.settings.allow_mock_services:
            return 100 * 1024 * 1024
        rows = await self.db.select(
            "profiles", {"select": "storage_quota_bytes", "id": f"eq.{user_id}", "limit": "1"}
        )
        return int(rows[0]["storage_quota_bytes"]) if rows else 0

    async def _save_record(self, record: dict[str, Any]) -> None:
        if self.db.settings.allow_mock_services:
            self._mock[record["id"]] = record
        else:
            await self.db.insert("attachments", record)
            await self.db.insert(
                "storage_objects",
                {
                    "user_id": record["user_id"],
                    "bucket": record["bucket"],
                    "object_key": record["object_key"],
                    "size_bytes": record["size_bytes"],
                    "object_type": "avatar"
                    if record["bucket"] == self.settings.minio_profile_bucket
                    else "attachment",
                },
            )

    async def _row(self, user_id: str, attachment_id: str) -> dict[str, Any]:
        if self.db.settings.allow_mock_services:
            row = self._mock.get(attachment_id)
            if row and row["user_id"] != user_id:
                row = None
        else:
            rows = await self.db.select(
                "attachments",
                {
                    "select": "*",
                    "id": f"eq.{attachment_id}",
                    "user_id": f"eq.{user_id}",
                    "deleted_at": "is.null",
                    "limit": "1",
                },
            )
            row = rows[0] if rows else None
        if not row:
            raise NotFoundError("Attachment tidak ditemukan.")
        return row

    async def presign(self, user_id: str, payload: PresignUploadRequest) -> PresignUploadResponse:
        if payload.content_type not in ALLOWED:
            from app.core.exceptions import AppError

            raise AppError("UNSUPPORTED_FILE_TYPE", "Jenis berkas tidak didukung.", 415)
        if payload.size_bytes > self.settings.max_upload_size_mb * 1024 * 1024:
            from app.core.exceptions import AppError

            raise AppError("ATTACHMENT_TOO_LARGE", "Ukuran attachment melebihi batas.", 413)
        validate_quota(await self._usage(user_id), payload.size_bytes, await self._quota(user_id))
        filename = safe_filename(payload.filename)
        bucket = (
            self.settings.minio_profile_bucket
            if payload.purpose == "avatar"
            else self.settings.minio_attachment_bucket
        )
        key = object_key(user_id, filename)
        aid = str(uuid4())
        record = {
            "id": aid,
            "user_id": user_id,
            "bucket": bucket,
            "object_key": key,
            "filename": filename,
            "mime_type": payload.content_type,
            "size_bytes": payload.size_bytes,
            "processing_status": "uploading",
            "verification_status": "pending",
            "confidence": 0.0,
            "created_at": self._now(),
        }
        await self._save_record(record)
        url = await self.storage.presigned_put(bucket, key, self.settings.presigned_url_expiry_seconds)
        return PresignUploadResponse(
            attachment_id=aid,
            object_key=key,
            upload_url=url,
            expires_in=self.settings.presigned_url_expiry_seconds,
        )

    async def _process(self, row: dict[str, Any], data: bytes, query: str) -> dict[str, Any]:
        extracted = self.extractor.extract(data, row["mime_type"])
        if extracted.get("needs_vision"):
            extracted = await self.image.analyze(data, row["mime_type"], query)
        update = {
            "processing_status": "completed",
            "verification_status": "extracted",
            "confidence": 0.8,
            "extracted_text": extracted.get("text", ""),
            "extraction_metadata": {k: v for k, v in extracted.items() if k != "text"},
        }
        row.update(update)
        if self.db.settings.allow_mock_services:
            self._mock[row["id"]] = row
        else:
            await self.db.update(
                "attachments", {"id": f"eq.{row['id']}", "user_id": f"eq.{row['user_id']}"}, update
            )
        return row

    async def complete(self, user_id: str, payload: AttachmentCompleteRequest) -> AttachmentStatusResponse:
        if self.db.settings.allow_mock_services:
            matches = [
                row
                for row in self._mock.values()
                if row["user_id"] == user_id and row["object_key"] == payload.object_key
            ]
        else:
            matches = await self.db.select(
                "attachments",
                {
                    "select": "*",
                    "user_id": f"eq.{user_id}",
                    "object_key": f"eq.{payload.object_key}",
                    "limit": "1",
                },
            )
        if not matches:
            raise NotFoundError("Metadata attachment tidak ditemukan.")
        row = matches[0]
        data = await self.storage.get(row["bucket"], row["object_key"])
        validate_upload(data, payload.filename, payload.content_type, self.settings)
        await self._process(row, data, "Analisis attachment ini")
        return await self.status(user_id, row["id"])

    async def upload(
        self, user_id: str, file: UploadFile, query: str = "Analisis attachment ini"
    ) -> FileUploadResponse:
        data = await file.read()
        filename = safe_filename(file.filename or "file")
        mime = validate_upload(data, filename, file.content_type or "application/octet-stream", self.settings)
        validate_quota(await self._usage(user_id), len(data), await self._quota(user_id))
        key = object_key(user_id, filename)
        aid = str(uuid4())
        bucket = self.settings.minio_attachment_bucket
        await self.storage.put(bucket, key, data, mime)
        record = {
            "id": aid,
            "user_id": user_id,
            "bucket": bucket,
            "filename": filename,
            "object_key": key,
            "mime_type": mime,
            "size_bytes": len(data),
            "processing_status": "processing",
            "verification_status": "pending",
            "confidence": 0.0,
            "created_at": self._now(),
        }
        await self._save_record(record)
        await self._process(record, data, query)
        preview = await self.storage.presigned_get(bucket, key, self.settings.presigned_url_expiry_seconds)
        info = AttachmentInfo(
            id=aid,
            filename=filename,
            stored_filename=key,
            mime_type=mime,
            preview_url=preview,
            processing_status="completed",
            detected_type=mime,
            verification_status="extracted",
            confidence=0.8,
        )
        return FileUploadResponse(
            file_id=aid,
            filename=filename,
            extracted_text=record.get("extracted_text", ""),
            content_type=mime,
            url=preview,
            attachment=info,
            context={"extracted_text": record.get("extracted_text", ""), "warnings": []},
        )

    async def status(self, user_id: str, attachment_id: str) -> AttachmentStatusResponse:
        row = await self._row(user_id, attachment_id)
        state = row.get("processing_status", "failed")
        return AttachmentStatusResponse(
            attachment_id=attachment_id,
            processing_status=state,
            progress=100 if state == "completed" else 50 if state in {"processing", "queued"} else 0,
            verification_status=row.get("verification_status", "pending"),
            confidence=row.get("confidence", 0),
            extracted_text=row.get("extracted_text"),
            detected_type=row.get("mime_type"),
            retryable=state == "failed",
        )

    async def delete(self, user_id: str, attachment_id: str) -> None:
        row = await self._row(user_id, attachment_id)
        await self.storage.delete(row["bucket"], row["object_key"])
        if self.db.settings.allow_mock_services:
            row["deleted_at"] = self._now()
        else:
            await self.db.update(
                "attachments",
                {"id": f"eq.{attachment_id}", "user_id": f"eq.{user_id}"},
                {"deleted_at": self._now()},
            )
            await self.db.update(
                "storage_objects",
                {"object_key": f"eq.{row['object_key']}", "user_id": f"eq.{user_id}"},
                {"deleted_at": self._now()},
            )

    async def context(self, user_id: str, ids: list[str]) -> list[dict[str, Any]]:
        contexts = []
        for attachment_id in ids:
            result = await self.status(user_id, attachment_id)
            if result.processing_status == "completed":
                contexts.append(
                    {
                        "attachment_id": attachment_id,
                        "text": result.extracted_text,
                        "detected_type": result.detected_type,
                    }
                )
        return contexts
