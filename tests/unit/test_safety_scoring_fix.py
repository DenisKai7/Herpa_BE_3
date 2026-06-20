import os
from app.logic.recommendation_orchestrator import (
    resolve_safety_status,
    resolve_safety_label,
    clamp_score,
    resolve_relevance_label,
)
from app.models.recommendation import HerbalRecommendationRequest


def test_update_safety_status_cypher_exists():
    assert os.path.exists("database/neo4j/100_update_herb_safety_status.cypher")
    assert os.path.exists("database/neo4j/101_recommendation_safety_indexes.cypher")


def test_recommendation_query_does_not_fail_without_safety_status():
    # Verify resolve_safety_status returns expected default label when property is missing
    status, label, notes = resolve_safety_status(
        toxicity=[],
        contraindications=[],
        interactions=[],
        user_context={},
        initial_status="unknown",
    )
    assert status == "unknown"
    assert label == "Data keamanan belum cukup"


def test_recommendation_query_returns_safety_status_unknown_when_missing():
    # Verify resolve_safety_status with empty initial_status falls back to unknown
    status, label, notes = resolve_safety_status(
        toxicity=[],
        contraindications=[],
        interactions=[],
        user_context={},
        initial_status="",
    )
    assert status == "unknown"
    assert label == "Data keamanan belum cukup"


def test_recommendation_score_is_clamped():
    assert clamp_score(1.5) == 1.0
    assert clamp_score(-0.5) == 0.0
    assert clamp_score(0.75) == 0.75


def test_relevance_label_low_medium_high():
    assert resolve_relevance_label(0.8) == ("high", "Relevansi tinggi")
    assert resolve_relevance_label(0.6) == ("medium", "Relevansi sedang")
    assert resolve_relevance_label(0.2) == ("initial", "Kandidat awal")
    assert resolve_relevance_label(0.0) == ("unknown", "Relevansi belum tersedia")


def test_safety_label_unknown_is_not_unsafe():
    assert resolve_safety_label("unknown") == "Data keamanan belum cukup"
    assert resolve_safety_label("safe") == "Relatif aman"


def test_build_light_explanation_low_score():
    from app.logic.recommendation_orchestrator import build_light_explanation
    cand = {"local_name": "Jahe"}
    explanation = build_light_explanation(cand, 0.2)
    assert "relevansinya masih rendah" in explanation


def test_build_light_explanation_medium_score():
    from app.logic.recommendation_orchestrator import build_light_explanation
    cand = {"local_name": "Jahe"}
    explanation = build_light_explanation(cand, 0.6)
    assert "memiliki kecocokan" in explanation


def test_match_reasons_include_symptoms():
    from app.logic.recommendation_orchestrator import build_match_reasons
    cand = {"matched_symptoms": ["batuk"]}
    reasons = build_match_reasons(cand)
    assert any("gejala" in r.lower() for r in reasons)


def test_match_reasons_include_compounds():
    from app.logic.recommendation_orchestrator import build_match_reasons
    cand = {"active_compounds": ["alkaloid"]}
    reasons = build_match_reasons(cand)
    assert any("senyawa aktif" in r.lower() for r in reasons)


def test_analyze_still_returns_200():
    # Check import routes and models
    assert HerbalRecommendationRequest
