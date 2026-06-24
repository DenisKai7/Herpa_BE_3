import pytest
import io
import asyncio
from types import SimpleNamespace
from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.models.auth import CurrentUser
from app.api.dependencies.services import get_services
from app.core.config import Settings
from app.services.supabase.client import SupabaseClient
from app.services.storage.minio_client import MinioStorage
from app.services.documents.extractor import DocumentExtractor
from app.services.documents.image_processor import ImageProcessor
from app.logic.attachment_orchestrator import AttachmentOrchestrator


@pytest.fixture()
def client_with_auth():
    settings = Settings(app_env="test", allow_mock_services=True)
    supabase = SupabaseClient(settings)
    storage = MinioStorage(settings)
    extractor = DocumentExtractor(settings)
    image = ImageProcessor(None)

    orchestrator = AttachmentOrchestrator(settings, storage, supabase, extractor, image)
    services = SimpleNamespace(
        settings=settings,
        attachments=orchestrator
    )

    async def user_one():
        return CurrentUser(id="11111111-1111-1111-1111-111111111111", email="u1@example.test")

    app.dependency_overrides[get_current_user] = user_one
    app.dependency_overrides[get_services] = lambda: services
    try:
        yield TestClient(app), orchestrator
    finally:
        app.dependency_overrides.clear()


def test_attachment_upload_flow(client_with_auth):
    client, orchestrator = client_with_auth

    file_content = b"Ini adalah isi dokumen test."
    file = io.BytesIO(file_content)

    response = client.post(
        "/api/files/upload",
        files={"file": ("test.txt", file, "text/plain")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["attachment"]["processing_status"] == "processing"

    file_id = data["file_id"]

    status_resp = client.get(f"/api/files/{file_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["processing_status"] in {"processing", "completed"}

    retry_resp = client.post(f"/api/files/{file_id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["processing_status"] in {"processing", "completed"}

    # Test debug and reprocess endpoints
    debug_resp = client.get(f"/api/files/{file_id}/vision-debug")
    assert debug_resp.status_code == 200
    debug_data = debug_resp.json()
    assert debug_data["attachment_id"] == file_id
    assert "visual_analysis" in debug_data

    reprocess_resp = client.post(f"/api/files/{file_id}/reprocess-vision")
    assert reprocess_resp.status_code == 200
    assert reprocess_resp.json()["processing_status"] in {"processing", "completed"}
