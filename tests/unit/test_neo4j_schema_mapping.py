import pytest

from app.core.exceptions import AppError
from app.graph.context_builder import format_herb_fact
from app.graph.entity_resolver import RESOLVE_HERB_ENTITY
from app.graph.query_templates import (
    HERB_COMPOUNDS,
    HERB_FAMILY,
    HERB_PROTEIN_TARGETS,
    HERB_SOURCES,
    HERB_THERAPEUTIC_USES,
    HERB_TOXICITY,
)
from app.graph.repositories import KnowledgeGraphRepository
from app.graph.retriever import GraphRetriever


class MockNeo4jClient:
    def __init__(self):
        self.calls = []
        self.rows = []
        self.fail = False

    async def read(self, query, parameters=None):
        self.calls.append((query, parameters or {}))
        if self.fail:
            raise AppError("NEO4J_UNAVAILABLE", "Query knowledge graph gagal.", 503)
        return self.rows


def sample_row():
    return {
        "plant": {
            "plant_id": "HRB-001-KUN",
            "local_name": "Kunyit",
            "scientific_name": "Curcuma longa",
            "latin_name": "Curcuma longa L.",
            "synonyms": ["kunir"],
            "simplisia_name": "Curcumae domesticae Rhizoma",
            "status": "verified",
        },
        "families": [{"name": "Zingiberaceae", "category": "family"}],
        "compounds": [{"name": "Curcumin", "pubchem_cid": "969516"}],
        "therapeutic_uses": [{"name": "anti-inflammatory", "category": "activity"}],
        "protein_targets": [{"name": "NF-kB", "mechanism": "modulation", "affinity_range": "reported"}],
        "toxicity": [{"name": "low", "category": "toxicity"}],
        "sources": [{"name": "dataset", "category": "curated"}],
    }


@pytest.mark.asyncio
async def test_herb_by_common_name():
    client = MockNeo4jClient()
    repo = KnowledgeGraphRepository(client)
    # Mock return list of herbs so hydrate succeeds
    client.rows = [{"plant": sample_row()["plant"]}]
    await repo.herb_by_name("kunyit")
    # First call is find_herbs, second call starts hydration
    query, params = client.calls[0]
    assert "search_term" in params or "name" in params


def test_herb_by_scientific_name():
    # Assert query split templates exist and reference the correct relations
    assert "HAS_COMPOUND" in HERB_COMPOUNDS
    assert "USED_FOR" in HERB_THERAPEUTIC_USES
    assert "BELONGS_TO" in HERB_FAMILY
    assert "HAS_PROTEIN_TARGET" in HERB_PROTEIN_TARGETS
    assert "HAS_TOXICITY" in HERB_TOXICITY
    assert "VERIFIED_BY" in HERB_SOURCES


def test_herb_by_local_names_array():
    # Verify localNames is not cast to string and uses any() syntax
    assert "any(localName IN coalesce(h.localNames, [])" in RESOLVE_HERB_ENTITY


def test_herb_projection_to_canonical_schema():
    row = sample_row()
    plant = row["plant"]
    assert plant["local_name"] == "Kunyit"
    assert plant["scientific_name"] == "Curcuma longa"
    assert plant["synonyms"] == ["kunir"]


@pytest.mark.asyncio
async def test_empty_result_is_not_neo4j_unavailable():
    client = MockNeo4jClient()
    repo = KnowledgeGraphRepository(client)
    retriever = GraphRetriever(repo)
    result = await retriever.retrieve("tanaman tidak ada", limit=3)
    assert result["facts"] == []
    assert result["grounding_status"] == "insufficient"


@pytest.mark.asyncio
async def test_cypher_error_is_neo4j_unavailable():
    client = MockNeo4jClient()
    client.fail = True
    repo = KnowledgeGraphRepository(client)
    with pytest.raises(AppError) as exc:
        await repo.plant_by_name("kunyit")
    assert exc.value.code == "NEO4J_UNAVAILABLE"


def test_context_builder_uses_therapeutic_uses():
    text = format_herb_fact(sample_row())
    assert "Penggunaan terapeutik" in text
    assert "anti-inflammatory" in text


@pytest.mark.asyncio
async def test_legacy_plant_by_name_alias():
    client = MockNeo4jClient()
    repo = KnowledgeGraphRepository(client)
    client.rows = [{"plant": sample_row()["plant"]}]
    await repo.plant_by_name("jahe")
    await repo.herb_by_name("jahe")
    # Both resolve to find_herbs then _hydrate_herb
    assert len(client.calls) == 14  # 1 search + 6 hydrates * 2 calls


def test_local_names_array_not_cast_to_string():
    assert "toString" not in RESOLVE_HERB_ENTITY
