import pytest
from neo4j.exceptions import CypherSyntaxError, SessionExpired

from app.core.config import Settings
from app.core.constants import ModelMode, Persona
from app.core.exceptions import AppError
from app.core.model_modes import normalize_model_mode
from app.graph.compound_normalizer import CompoundNormalizer
from app.graph.neo4j_client import Neo4jClient
from app.graph.query_templates import (
    HERB_COMPOUNDS,
    HERB_FAMILY,
    HERB_PROTEIN_TARGETS,
    HERB_SOURCES,
    HERB_THERAPEUTIC_USES,
    HERB_TOXICITY,
)
from app.prompts.persona_response_policy import persona_policy


class MockTx:
    def __init__(self):
        self.run_calls = []
        self.fail_on_run = False
        self.fail_exc = None

    async def run(self, query, parameters, timeout=None):
        self.run_calls.append((query, parameters))
        if self.fail_on_run:
            raise self.fail_exc
        return self


class MockSession:
    def __init__(self, tx):
        self.tx = tx

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def execute_read(self, fn, *args):
        return await fn(self.tx, *args)


class MockDriver:
    def __init__(self, tx):
        self.tx = tx
        self.session_calls = []

    def session(self, database=None):
        self.session_calls.append(database)
        return MockSession(self.tx)

    async def close(self):
        pass


def test_thinking_hard_alias_maps_to_thinking_high():
    assert normalize_model_mode("thinking-hard") == ModelMode.THINKING_HIGH
    assert normalize_model_mode("thinking_hard") == ModelMode.THINKING_HIGH


def test_compound_deduplication():
    raw = [
        {"name": "Curcumin", "pubchem_cid": "969516"},
        {"name": "curcumin", "pubchem_cid": "969516"},
        {"name": "Bisdemethoxycurcumin", "pubchem_cid": "5469774"},
        {"name": "Curcumin", "pubchem_cid": ""},
    ]
    deduped = CompoundNormalizer.deduplicate(raw)
    # Deduplicates by CID and name normalization
    assert len(deduped) == 2
    assert deduped[0]["name"] == "Curcumin"
    assert deduped[1]["name"] == "Bisdemethoxycurcumin"


def test_persona_umum_hides_raw_iupac():
    policy = persona_policy(Persona.UMUM, ModelMode.FAST_MEDIUM)
    assert "Jangan menampilkan nama IUPAC mentah" in policy


def test_persona_pelajar_uses_educational_structure():
    policy = persona_policy(Persona.PELAJAR, ModelMode.FAST_MEDIUM)
    assert "Definisi singkat" in policy or "Konsep utama" in policy


def test_persona_peneliti_includes_evidence_sections():
    policy = persona_policy(Persona.PENELITI, ModelMode.THINKING_HIGH)
    assert "Fitokimia" in policy or "Marker compound" in policy


def test_persona_tenaga_medis_enforces_safety():
    policy = persona_policy(Persona.TENAGA_MEDIS, ModelMode.THINKING_HIGH)
    assert "Safety review" in policy or "Interaksi" in policy


def test_neo4j_query_does_not_create_cartesian_explosion():
    # Verify relations are queried independently (no optional match joins in split templates)
    for q in (
        HERB_COMPOUNDS,
        HERB_FAMILY,
        HERB_PROTEIN_TARGETS,
        HERB_SOURCES,
        HERB_THERAPEUTIC_USES,
        HERB_TOXICITY,
    ):
        assert "OPTIONAL MATCH" not in q
        assert "collect(" not in q


@pytest.mark.asyncio
async def test_session_expired_is_retried():
    settings = Settings(
        app_env="test",
        allow_mock_services=False,
        neo4j_max_retry_attempts=2,
        neo4j_retry_base_delay_ms=1,
    )
    client = Neo4jClient(settings)
    tx = MockTx()
    tx.fail_on_run = True
    tx.fail_exc = SessionExpired("session expired")
    client.driver = MockDriver(tx)

    with pytest.raises(AppError) as exc:
        await client.read("MATCH (n) RETURN n")
    assert exc.value.code == "NEO4J_UNAVAILABLE"
    # 1 initial run + 2 retries = 3 calls total
    assert len(tx.run_calls) == 3


@pytest.mark.asyncio
async def test_non_retryable_cypher_error_is_not_retried():
    settings = Settings(
        app_env="test",
        allow_mock_services=False,
        neo4j_max_retry_attempts=2,
        neo4j_retry_base_delay_ms=1,
    )
    client = Neo4jClient(settings)
    tx = MockTx()
    tx.fail_on_run = True
    tx.fail_exc = CypherSyntaxError("syntax error")
    client.driver = MockDriver(tx)

    with pytest.raises(AppError) as exc:
        await client.read("MATCH (n) RETURN n")
    assert exc.value.code == "NEO4J_UNAVAILABLE"
    # No retries for syntax error, only 1 call
    assert len(tx.run_calls) == 1
