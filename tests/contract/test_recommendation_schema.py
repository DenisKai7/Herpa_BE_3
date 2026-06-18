from app.models.recommendation import HerbalRecommendationResponse


def test_recommendation_contract():
    result = HerbalRecommendationResponse(status="completed", request_id="r1")
    data = result.model_dump(mode="json")
    assert "recommendations" in data and "options" in data
    assert data["request_id"] == "r1"
