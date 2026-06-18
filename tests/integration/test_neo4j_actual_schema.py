import os

import pytest

from app.core.config import get_settings
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_NEO4J_INTEGRATION_TESTS", "false").lower() != "true",
    reason="Set RUN_NEO4J_INTEGRATION_TESTS=true to query Neo4j Aura",
)


@pytest.mark.asyncio
async def test_actual_neo4j_herb_schema_kunyit_jahe():
    settings = get_settings()
    client = Neo4jClient(settings)
    repo = KnowledgeGraphRepository(client)
    try:
        assert await client.health() is True
        for name in ("kunyit", "jahe"):
            rows = await repo.plant_by_name(name, limit=3)
            assert rows
            assert rows[0].get("plant", {}).get("local_name") or rows[0].get("plant", {}).get(
                "scientific_name"
            )
    finally:
        await client.close()
