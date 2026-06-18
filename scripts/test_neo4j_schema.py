from __future__ import annotations

import asyncio
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=True)
except Exception:
    pass

from app.core.config import get_settings  # noqa: E402
from app.graph.neo4j_client import Neo4jClient  # noqa: E402
from app.graph.repositories import KnowledgeGraphRepository  # noqa: E402


def safe_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )


def ok(message: str) -> None:
    print(f"[OK] {safe_text(message)}")


def fail(message: str) -> None:
    print(f"[FAIL] {safe_text(message)}")


async def main() -> int:
    settings = get_settings()
    client = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(client)
    try:
        if not await client.health():
            fail("Neo4j connected")
            return 1
        ok("Neo4j connected")
        ok(f"Database: {settings.neo4j_database}")

        herb_count = await client.read("MATCH (h:Herb) RETURN count(h) AS count", {})
        ok(f"Herb nodes: {herb_count[0].get('count', 0) if herb_count else 0}")

        rel_count = await client.read("MATCH ()-[r:HAS_COMPOUND]->() RETURN count(r) AS count", {})
        ok(f"HAS_COMPOUND relationships: {rel_count[0].get('count', 0) if rel_count else 0}")

        status = 0
        for name in ("kunyit", "jahe"):
            rows = await repo.plant_by_name(name, limit=3)
            if not rows:
                fail(f"{name.title()} found")
                status = 1
                continue
            plant = rows[0].get("plant") or {}
            ok(f"{name.title()} found: {plant.get('plant_id') or plant.get('scientific_name')}")
            print("[OK] Compounds:", safe_text(", ".join(_names(rows[0].get("compounds", []))[:10]) or "-"))
            print(
                "[OK] Therapeutic uses:",
                safe_text(", ".join(_names(rows[0].get("therapeutic_uses", []))[:10]) or "-"),
            )
            print(
                "[OK] Protein targets:",
                safe_text(", ".join(_names(rows[0].get("protein_targets", []))[:10]) or "-"),
            )
            print("[OK] Toxicity:", safe_text(", ".join(_names(rows[0].get("toxicity", []))[:10]) or "-"))
            print("[OK] Sources:", safe_text(", ".join(_names(rows[0].get("sources", []))[:10]) or "-"))
        return status
    finally:
        await client.close()


def _names(items):
    return [str(item.get("name")) for item in items if isinstance(item, dict) and item.get("name")]


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
