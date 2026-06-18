from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import Settings  # noqa: E402


def line(status: str, message: str) -> None:
    print(f"[{status}] {message}")


async def main() -> int:
    settings = Settings()
    failed = False

    if Path(".env").exists():
        line("OK", ".env terbaca")
    else:
        line("INFO", ".env tidak ditemukan; memakai environment/default")

    if settings.supabase_url:
        line("OK", "Supabase configuration")
    else:
        line("FAIL", "Supabase configuration missing")
        failed = True

    if settings.neo4j_uri:
        line("OK", "Neo4j configuration")
    else:
        line("FAIL", "Neo4j configuration missing")
        failed = True

    if settings.minio_endpoint:
        line("OK", f"MinIO endpoint configured: {settings.minio_endpoint}")
    else:
        line("FAIL", "MinIO endpoint missing")
        failed = True

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            res = await client.get(f"{settings.llama_text_base_url.rstrip('/')}/models")
            res.raise_for_status()
            models = [item.get("id") for item in res.json().get("data", [])]
            resolved = (
                settings.llama_text_model_name
                if settings.llama_text_model_name in models
                else (models[0] if len(models) == 1 else None)
            )
            line("OK", "llama.cpp text server reachable")
            line("OK" if resolved else "FAIL", f"Resolved model: {resolved or 'not resolved'}")
            failed = failed or not bool(resolved)
        except Exception as exc:
            line("FAIL", f"llama.cpp text server: {exc}")
            failed = True

        line("OK", f"Context size: {settings.text_model_context_size}")
        line("INFO", "Vision enabled" if settings.enable_vision else "Vision disabled")

        for path in ("/api/v1/health/live", "/api/v1/health/models"):
            try:
                res = await client.get(f"http://127.0.0.1:{settings.backend_port}{path}")
                line("OK" if res.status_code < 500 else "FAIL", f"FastAPI {path}: {res.status_code}")
            except Exception as exc:
                line("FAIL", f"FastAPI {path}: {exc}")
                failed = True

    line("OK", "Model mode: fast-medium")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
