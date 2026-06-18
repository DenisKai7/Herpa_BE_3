from app.core.config import Settings
from app.core.exceptions import AppError
from app.services.documents.pdf_extractor import extract_pdf
from app.services.documents.docx_extractor import extract_docx
from app.services.documents.spreadsheet_extractor import extract_csv, extract_xlsx


class DocumentExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings

    def extract(self, data: bytes, mime_type: str) -> dict:
        try:
            if mime_type == "application/pdf":
                return extract_pdf(data, self.settings)
            if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return extract_docx(data, self.settings)
            if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                return extract_xlsx(data, self.settings)
            if mime_type == "text/csv":
                return extract_csv(data, self.settings)
            if mime_type in {"text/plain", "text/markdown"}:
                text = data.decode("utf-8-sig", errors="replace")
                return {
                    "text": text[: self.settings.max_document_characters],
                    "truncated": len(text) > self.settings.max_document_characters,
                    "needs_vision": False,
                }
            if mime_type.startswith("image/"):
                return {"text": "", "needs_vision": True, "truncated": False}
        except Exception as exc:
            raise AppError("ATTACHMENT_PROCESSING_FAILED", "Dokumen gagal diekstrak.", 422) from exc
        raise AppError("UNSUPPORTED_FILE_TYPE", "Jenis dokumen belum didukung.", 415)
