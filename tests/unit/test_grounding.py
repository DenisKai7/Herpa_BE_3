from app.graph.grounding_validator import validate_grounding


def test_insufficient_without_sources():
    result = validate_grounding("jawaban", {"facts": []}, [])
    assert result["status"] == "insufficient"


def test_grounded_with_graph_fact():
    result = validate_grounding("jawaban", {"facts": [{"plant": "jahe"}]}, [])
    assert result["status"] == "grounded"
    assert result["confidence"] > 0.5
