import json
from datetime import datetime
from decimal import Decimal

from neo4j.time import Date, DateTime, Duration, Time
from pydantic import BaseModel

from app.core.json_safety import json_safe
from app.models.recommendation import HerbalCandidate


class ExampleModel(BaseModel):
    value: object


def test_json_safe_converts_neo4j_datetime():
    value = {"updatedAt": DateTime(2026, 6, 18, 12, 0, 0)}

    result = json_safe(value)

    assert isinstance(result["updatedAt"], str)


def test_json_safe_converts_neo4j_date():
    result = json_safe({"date": Date(2026, 6, 18)})

    assert isinstance(result["date"], str)


def test_json_safe_converts_neo4j_time():
    result = json_safe({"time": Time(12, 0, 0)})

    assert isinstance(result["time"], str)


def test_json_safe_converts_neo4j_duration():
    result = json_safe({"duration": Duration(months=1, days=2, seconds=3)})

    assert isinstance(result["duration"], str)


def test_json_safe_converts_nested_neo4j_datetime():
    value = {
        "herb": {
            "name": "Kencur",
            "metadata": {"updatedAt": DateTime(2026, 6, 18, 12, 0, 0)},
        }
    }

    result = json_safe(value)

    assert isinstance(result["herb"]["metadata"]["updatedAt"], str)


def test_json_safe_converts_pydantic_model():
    result = json_safe(ExampleModel(value=DateTime(2026, 6, 18, 12, 0, 0)))

    assert isinstance(result["value"], str)


def test_recommendation_candidate_with_neo4j_datetime_serializes():
    candidate = HerbalCandidate(
        plant_id="h1",
        local_name="Kencur",
        scientific_name="Kaempferia galanga L.",
        evidence_sources=[{"updatedAt": DateTime(2026, 6, 18, 12, 0, 0)}],
    )

    payload = json_safe(candidate.model_dump(mode="python"))

    assert isinstance(payload["evidence_sources"][0]["updatedAt"], str)
    json.dumps(payload)


def test_recommendation_result_payload_is_json_safe():
    candidate = HerbalCandidate(
        plant_id="h1",
        local_name="Kencur",
        scientific_name="Kaempferia galanga L.",
        evidence_sources=[{"updatedAt": DateTime(2026, 6, 18, 12, 0, 0), "score": Decimal("0.5")}],
    )

    result_payload = json_safe({"result": candidate.model_dump(mode="python"), "created_at": datetime(2026, 6, 18)})

    assert isinstance(result_payload["result"]["evidence_sources"][0]["updatedAt"], str)
    assert result_payload["result"]["evidence_sources"][0]["score"] == 0.5
    json.dumps(result_payload)


def test_neo4j_repository_returns_json_safe_rows():
    row = {"source": {"updatedAt": DateTime(2026, 6, 18, 12, 0, 0)}}

    result = json_safe(row)

    assert isinstance(result["source"]["updatedAt"], str)


def test_recommendation_analyze_does_not_500_on_neo4j_datetime():
    candidate = HerbalCandidate(
        plant_id="h1",
        local_name="Kencur",
        scientific_name="Kaempferia galanga L.",
        evidence_sources=[{"updatedAt": DateTime(2026, 6, 18, 12, 0, 0)}],
    )

    result = json_safe(candidate.model_dump(mode="python"))

    json.dumps(result)
