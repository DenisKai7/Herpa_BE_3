import asyncio
from datetime import timedelta
from io import BytesIO
from minio import Minio
from app.core.config import Settings
from app.core.exceptions import AppError


class MinioStorage:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            if not settings.allow_mock_services
            else None
        )
        self._mock: dict[tuple[str, str], bytes] = {}

    async def ensure_buckets(self) -> None:
        if self.client is None:
            return
        for bucket in [
            self.settings.minio_profile_bucket,
            self.settings.minio_attachment_bucket,
            self.settings.minio_export_bucket,
            self.settings.minio_temp_bucket,
        ]:
            exists = await asyncio.to_thread(self.client.bucket_exists, bucket)
            if not exists:
                await asyncio.to_thread(self.client.make_bucket, bucket)

    async def health(self) -> bool:
        if self.client is None:
            return True
        try:
            client = self.client
            assert client is not None
            await asyncio.to_thread(lambda: list(client.list_buckets()))
            return True
        except Exception:
            return False

    async def put(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        if self.client is None:
            self._mock[(bucket, key)] = data
            return
        try:
            await asyncio.to_thread(
                self.client.put_object, bucket, key, BytesIO(data), len(data), content_type
            )
        except Exception as exc:
            raise AppError("MINIO_UNAVAILABLE", "Penyimpanan berkas tidak tersedia.", 503) from exc

    async def get(self, bucket: str, key: str) -> bytes:
        if self.client is None:
            return self._mock.get((bucket, key), b"")
        response = await asyncio.to_thread(self.client.get_object, bucket, key)
        try:
            return await asyncio.to_thread(response.read)
        finally:
            response.close()
            response.release_conn()

    async def delete(self, bucket: str, key: str) -> None:
        if self.client is None:
            self._mock.pop((bucket, key), None)
            return
        await asyncio.to_thread(self.client.remove_object, bucket, key)

    async def list_keys(self, bucket: str, prefix: str = "") -> list[dict[str, object]]:
        if self.client is None:
            return [
                {"object_name": key, "size": len(data)}
                for (item_bucket, key), data in self._mock.items()
                if item_bucket == bucket and key.startswith(prefix)
            ]
        client = self.client
        assert client is not None

        def _list() -> list[dict[str, object]]:
            return [
                {
                    "object_name": item.object_name,
                    "size": item.size or 0,
                    "last_modified": item.last_modified.isoformat() if item.last_modified else None,
                }
                for item in client.list_objects(bucket, prefix=prefix, recursive=True)
            ]

        return await asyncio.to_thread(_list)

    async def presigned_put(self, bucket: str, key: str, seconds: int) -> str:
        if self.client is None:
            return f"http://localhost/mock-upload/{bucket}/{key}"
        return await asyncio.to_thread(
            self.client.presigned_put_object, bucket, key, timedelta(seconds=seconds)
        )

    async def presigned_get(self, bucket: str, key: str, seconds: int) -> str:
        if self.client is None:
            return f"http://localhost/mock-download/{bucket}/{key}"
        return await asyncio.to_thread(
            self.client.presigned_get_object, bucket, key, timedelta(seconds=seconds)
        )
