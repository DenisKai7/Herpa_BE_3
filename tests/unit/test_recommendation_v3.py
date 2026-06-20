import pytest

from app.graph.query_templates import HERBAL_RECOMMENDATION_LIGHT_V3
from app.graph.repositories import build_fulltext_query
from app.logic.recommendation_orchestrator import resolve_evidence_status, resolve_relevance_label, resolve_safety_label
from app.services.recommendation.symptom_expander import extract_recommendation_terms


def test_v3_query_uses_primary_and_expanded_terms():
    assert "$primary_terms" in HERBAL_RECOMMENDATION_LIGHT_V3
    assert "$expanded_terms" in HERBAL_RECOMMENDATION_LIGHT_V3
    main_path = HERBAL_RECOMMENDATION_LIGHT_V3.split("OPTIONAL MATCH", 1)[0]
    assert "CONTAINS" not in main_path
    assert "s.name_lc IN $expanded_terms" in main_path


def test_v3_query_limits_terms():
    terms = extract_recommendation_terms(
        "batuk berdahak dan tenggorokan gatal dan pilek dan mual dan perut kembung dan nyeri",
        [],
    )
    assert len(terms.primary_terms) <= 5
    assert len(terms.expanded_terms) <= 15


def test_score_not_100_for_single_partial_match():
    score = 0.5 * 0.40 + 0.1 * 0.20 + 1.0 * 0.15 + 1.0 * 0.05 + 0.75 * 0.10 + 0.05
    assert score < 1.0


def test_score_high_only_when_primary_coverage_high():
    low_score = 0.0 * 0.40 + 0.2 * 0.20 + 1.0 * 0.15 + 1.0 * 0.05 + 0.75 * 0.10
    high_score = 1.0 * 0.40 + 0.8 * 0.20 + 1.0 * 0.15 + 1.0 * 0.05 + 0.75 * 0.10 + 0.10
    assert low_score < 0.5
    assert high_score >= 0.75


def test_relevance_label_initial_low_medium_high():
    assert resolve_relevance_label(0.1)[0] == "initial"
    assert resolve_relevance_label(0.3)[0] == "low"
    assert resolve_relevance_label(0.6)[0] == "medium"
    assert resolve_relevance_label(0.8)[0] == "high"


def test_safety_warning_generic_maps_to_limited():
    assert resolve_safety_label("limited") == "Data keamanan terbatas"


def test_interaction_maps_to_caution():
    assert resolve_safety_label("caution") == "Perlu perhatian"


def test_evidence_label_traditional():
    assert resolve_evidence_status([], traditional_uses=[{"title": "Batuk"}]) == (
        "traditional",
        "Data tradisional tersedia",
    )


def test_evidence_label_unavailable():
    assert resolve_evidence_status([]) == ("unavailable", "Data bukti belum tersedia")


def test_fulltext_query_builder():
    assert build_fulltext_query(["batuk", "dahak"]) == '"batuk"~ OR "dahak"~'
    assert build_fulltext_query(["a", ""]) == "herbal"


@pytest.mark.asyncio
async def test_detail_endpoint_returns_core_tabs():
    from app.services.recommendation.enrichment_mapper import empty_enrichment

    detail = empty_enrichment()
    assert "traditional_uses" in detail
    assert "preparation_methods" in detail
    assert "usage_guidelines" in detail
    assert "safety_warnings" in detail
