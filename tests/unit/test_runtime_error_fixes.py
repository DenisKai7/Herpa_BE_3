import pytest

from app.core.config import Settings
from app.core.constants import Persona
from app.core.exceptions import AppError
from app.graph.compound_normalizer import CompoundNormalizer
from app.services.ai.context_budget import fit_messages_to_context
from app.graph.neo4j_client import Neo4jClient
from app.graph.repositories import KnowledgeGraphRepository
from app.services.ai.complexity import assess_complexity
from app.services.ai.text_client import OpenAICompatibleClient


class MockTx:
    def __init__(self):
        self.run_calls = []
        self.fail_exc = None

    async def run(self, query, parameters, timeout=None):
        self.run_calls.append((query, parameters))
        if self.fail_exc:
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

    def session(self, database=None):
        return MockSession(self.tx)

    async def close(self):
        pass


class MockResponse:
    def __init__(self, status_code, text_data, headers=None):
        self.status_code = status_code
        self.text = text_data
        self.headers = headers or {}

    def json(self):
        import json

        return json.loads(self.text)


class MockAsyncClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    async def post(self, url, json, **kwargs):
        self.calls.append((url, json))
        return self.responses.pop(0)

    async def get(self, url, **kwargs):
        return MockResponse(200, '{"data": [{"id": "Qwen3-4B-Instruct-2507"}]}')


@pytest.mark.asyncio
async def test_missing_fulltext_index_uses_fallback():
    client = Neo4jClient(Settings(app_env="test", allow_mock_services=False))
    tx = MockTx()
    # Simulate first query throwing missing index error
    tx.fail_exc = AppError(
        "NEO4J_UNAVAILABLE",
        "Query failed",
        503,
        {"reason": "there is no such fulltext schema index herb_fulltext_idx"},
    )
    client.driver = MockDriver(tx)
    repo = KnowledgeGraphRepository(client)

    # Mock fallback to return empty list instead of raising
    client.read_original = client.read

    async def mock_read(query, parameters=None):
        if "db.index.fulltext.queryNodes" in query:
            raise AppError(
                "NEO4J_UNAVAILABLE",
                "Query failed",
                503,
                {"reason": "there is no such fulltext schema index herb_fulltext_idx"},
            )
        return [{"plant": {"plant_id": "test"}}]

    client.read = mock_read
    results = await repo.find_herbs("kunyit", limit=3)
    assert len(results) == 1
    assert results[0]["plant"]["plant_id"] == "test"


@pytest.mark.asyncio
async def test_llama_400_logs_response_body():
    client = OpenAICompatibleClient("http://127.0.0.1:8080/v1", "Qwen3", 10.0)
    mock_response = MockResponse(400, "invalid parameter 'unknown_field'")
    client.client = MockAsyncClient([mock_response])

    with pytest.raises(AppError) as exc:
        await client.complete([{"role": "user", "content": "hi"}])
    assert exc.value.code == "MODEL_REQUEST_INVALID"
    assert "unknown_field" in exc.value.details["response_body"]


@pytest.mark.asyncio
async def test_real_context_error_maps_to_context_overflow():
    client = OpenAICompatibleClient("http://127.0.0.1:8080/v1", "Qwen3", 10.0)
    mock_response = MockResponse(400, "exceeds the context window length")
    client.client = MockAsyncClient([mock_response])

    with pytest.raises(AppError) as exc:
        await client.complete([{"role": "user", "content": "hi"}])
    assert exc.value.code == "MODEL_CONTEXT_OVERFLOW"
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_unsupported_field_retry_once():
    client = OpenAICompatibleClient("http://127.0.0.1:8080/v1", "Qwen3", 10.0)
    # First response: 400 with 'cache_prompt' unsupported error
    # Second response: 200 success completion
    resp1 = MockResponse(400, "unknown parameter 'cache_prompt'")
    resp2 = MockResponse(200, '{"choices": [{"message": {"content": "jawaban"}}], "usage": {}}')

    mock_http = MockAsyncClient([resp1, resp2])
    client.client = mock_http

    result = await client.complete([{"role": "user", "content": "hi"}], cache_prompt=True)
    assert result["choices"][0]["message"]["content"] == "jawaban"
    # Ensure it made exactly 2 calls and removed the parameter
    assert len(mock_http.calls) == 2
    assert "cache_prompt" not in mock_http.calls[1][1]


def test_fast_medium_context_budget():
    messages = [
        {"role": "system", "content": "safety prompt"},
        {
            "role": "user",
            "content": "FAKTA KNOWLEDGE GRAPH:\n"
            + "deskripsi mikroskopis\n" * 100
            + "iupac name\n" * 50
            + "Jahe",
        },
    ]
    # Estimate should trim microscopic / iupac
    fitted = fit_messages_to_context(
        messages, context_size=512, max_output_tokens=100, safety_margin=50, persona="umum", user_query="Jahe"
    )
    content = fitted[1]["content"]
    assert "mikroskopis" not in content.lower()
    assert "iupac" not in content.lower()


def test_thinking_high_simple_query_one_call():
    assessment = assess_complexity("Senyawa aktif jahe", Persona.UMUM)
    assert assessment.requires_refinement is False


def test_thinking_high_complex_query_refines():
    assessment = assess_complexity(
        "Bandingkan efek samping dan interaksi jahe vs kunyit", Persona.TENAGA_MEDIS
    )
    assert assessment.requires_refinement is True


def test_persona_umum_hides_iupac():
    compounds = [{"name": "Gingerol", "iupac": "1-(4-hydroxy-3-methoxyphenyl)decan-3-one"}]
    deduped = CompoundNormalizer.deduplicate(compounds, persona="umum")
    assert deduped[0]["iupac"] is None
