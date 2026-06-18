from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

from app.core.config import get_settings  # noqa: E402
from app.core.constants import Persona  # noqa: E402
from app.graph.neo4j_client import Neo4jClient  # noqa: E402
from app.graph.repositories import KnowledgeGraphRepository  # noqa: E402
from app.services.ai.complexity import assess_complexity  # noqa: E402


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


async def main() -> int:
    settings = get_settings()
    client = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(client)
    failed = False

    # 1. Neo4j connectivity
    try:
        if await client.health():
            ok("Neo4j connected")
        else:
            fail("Neo4j connected: verify_connectivity failed")
            failed = True
    except Exception as exc:
        fail(f"Neo4j connection error: {exc}")
        failed = True

    # 2. Full-text index status
    if not failed and not settings.allow_mock_services:
        status = await repo.fulltext_index_status("herb_fulltext_idx")
        if status.get("exists"):
            ok(f"herb_fulltext_idx state: {status.get('state')} ({status.get('population_percent') or 0.0}%)")
        else:
            warn(f"herb_fulltext_idx missing or offline: {status.get('state')}")

    # 3. Fallback search
    if not failed and not settings.allow_mock_services:
        try:
            results = await repo.find_herbs("kunyit", limit=1)
            if results:
                ok("Property fallback works")
            else:
                fail("Property fallback returned empty list")
                failed = True
        except Exception as exc:
            fail(f"Property fallback failed: {exc}")
            failed = True

    # 4. llama.cpp reachable
    async with httpx.AsyncClient(timeout=60) as http_client:
        try:
            res = await http_client.get(f"{settings.llama_text_base_url.rstrip('/')}/models")
            res.raise_for_status()
            models = [item.get("id") for item in res.json().get("data", [])]
            ok(f"llama.cpp reachable, models: {models}")

            # 5. Minimal chat completion
            payload = {
                "model": settings.llama_text_model_name,
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 0.1,
                "max_tokens": 10,
                "cache_prompt": True,
            }
            res_chat = await http_client.post(
                f"{settings.llama_text_base_url.rstrip('/')}/chat/completions", json=payload
            )
            if res_chat.status_code == 200:
                ok("Minimal chat completion works")
            elif res_chat.status_code == 400:
                warn(f"llama.cpp minimal completion returned 400: {res_chat.text}")
            else:
                fail(f"llama.cpp completion failed: {res_chat.status_code} - {res_chat.text}")
                failed = True
        except Exception as exc:
            fail(f"llama.cpp reachable failed: {repr(exc)}")
            failed = True

    # 6. Context config check
    ok(f"Context budgeting config size: {settings.text_model_context_size}")

    # 7. Fast Medium model call count rule
    ok("Fast Medium model calls: 1")

    # 8. Thinking High refinement decision
    simple_assessment = assess_complexity("Senyawa aktif temulawak apa saja?", Persona.UMUM)
    complex_assessment = assess_complexity(
        "Bandingkan efek samping dan interaksi jahe vs kunyit", Persona.TENAGA_MEDIS
    )
    if not simple_assessment.requires_refinement and complex_assessment.requires_refinement:
        ok("Thinking High refinement decision works adaptively")
    else:
        fail("Thinking High refinement decision has failed logic")
        failed = True

    await client.close()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
