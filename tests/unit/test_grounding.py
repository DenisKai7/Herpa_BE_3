from app.graph.grounding_validator import validate_grounding


def test_insufficient_without_sources():
    result = validate_grounding("jawaban", {"facts": []}, [])
    assert result["status"] == "insufficient"


def test_grounded_with_graph_fact():
    result = validate_grounding("jawaban", {"facts": [{"plant": "jahe"}]}, [])
    assert result["status"] == "grounded"
    assert result["confidence"] > 0.5


def test_vlm_grounding():
    result = validate_grounding("jawaban", {"facts": []}, [], attachments=[{"plant_candidates": [{"local_name": "sirih"}]}])
    assert result["status"] == "vlm_identified"
    assert result["confidence"] == 0.60

    result = validate_grounding("jawaban", {"facts": [{"plant": "jahe"}]}, [], attachments=[{"plant_candidates": [{"local_name": "jahe"}]}])
    assert result["status"] == "grounded"
    assert result["confidence"] > 0.60

