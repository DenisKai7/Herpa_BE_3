import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_services
from app.main import app
from app.models.auth import CurrentUser
from app.models.recommendation import AgeGroup, HerbalRecommendationRequest, HerbalRecommendationResponse


def test_recommendation_contract():
    result = HerbalRecommendationResponse(status="completed", request_id="r1")
    data = result.model_dump(mode="json")
    assert "recommendations" in data and "options" in data
    assert data["request_id"] == "r1"


def test_age_group_accepts_null():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak",
            "age_group": None,
        }
    )

    assert req.age_group is None


def test_age_group_accepts_empty_string():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak",
            "age_group": "",
        }
    )

    assert req.age_group is None


def test_age_group_accepts_dewasa_alias():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak",
            "age_group": "dewasa",
        }
    )

    assert req.age_group == AgeGroup.ADULT


def test_age_group_accepts_adult():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak",
            "age_group": "adult",
        }
    )

    assert req.age_group == AgeGroup.ADULT


def test_age_group_rejects_invalid_value_with_clear_error():
    with pytest.raises(ValidationError) as exc_info:
        HerbalRecommendationRequest.model_validate(
            {
                "complaint": "batuk berdahak",
                "age_group": "paruh baya",
            }
        )

    errors = exc_info.value.errors()
    assert errors[0]["loc"] == ("age_group",)
    assert errors[0]["type"] in {"enum", "literal_error"}


def test_recommendation_request_accepts_complaint_only():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak dan tenggorokan gatal",
        }
    )

    assert req.complaint == "batuk berdahak dan tenggorokan gatal"
    assert req.free_text == "batuk berdahak dan tenggorokan gatal"
    assert req.symptoms == []
    assert req.persona == "umum"
    assert req.model_choice == "fast-medium"
    assert req.age_group is None
    assert req.pregnancy_status is None
    assert req.allergies == []
    assert req.current_medications == []
    assert req.medical_conditions == []


def test_recommendation_request_accepts_legacy_keluhan():
    req = HerbalRecommendationRequest.model_validate({"keluhan": "batuk berdahak"})

    assert req.complaint == "batuk berdahak"
    assert req.free_text == "batuk berdahak"


def test_recommendation_request_accepts_message_alias():
    req = HerbalRecommendationRequest.model_validate({"message": "tenggorokan gatal"})

    assert req.complaint == "tenggorokan gatal"
    assert req.free_text == "tenggorokan gatal"


def test_recommendation_empty_optional_fields_do_not_422():
    req = HerbalRecommendationRequest.model_validate(
        {
            "complaint": "batuk berdahak",
            "symptoms": "",
            "age_group": "",
            "pregnancy_status": "undefined",
            "allergies": "",
            "current_medications": None,
            "medical_conditions": "null",
        }
    )

    assert req.symptoms == []
    assert req.age_group is None
    assert req.pregnancy_status is None
    assert req.allergies == []
    assert req.current_medications == []
    assert req.medical_conditions == []


def test_validation_error_response_shape():
    async def fake_current_user() -> CurrentUser:
        return CurrentUser(id="user-1", email="user@example.test")

    app.dependency_overrides[get_current_user] = fake_current_user
    app.dependency_overrides[get_services] = lambda: object()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/herbal-recommendations/analyze",
            json={"complaint": "batuk berdahak", "age_group": "paruh baya"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Format request tidak sesuai."
    assert body["error"]["details"][0]["loc"] == ["body", "age_group"]
