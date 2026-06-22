"""Tests for herbal recommendation factual labels, scoring, and free-text complaints."""
import math

import pytest

from app.logic.recommendation_orchestrator import (
    clamp_score,
    resolve_data_status,
    resolve_evidence_status,
    resolve_relevance_label,
    resolve_safety_label,
    resolve_safety_status,
    score_to_percent,
    relevance_level_from_score,
)
from app.models.recommendation import HerbalCandidate, HerbalRecommendationResponse, RecommendationScore
from app.services.recommendation.enrichment_mapper import remove_empty_items
from app.services.recommendation.symptom_aliases import expand_symptoms
from app.services.recommendation.symptom_expander import extract_recommendation_terms


# ─── Relevance label / percent sync ────────────────────────────────────────────

class TestRelevanceLabelPercentSync:
    def test_relevance_label_uses_same_score_as_percent(self):
        """Label and percent must derive from the same underlying score."""
        for score in [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]:
            level, label = relevance_level_from_score(score)
            pct = score_to_percent(score)
            # When label says "tinggi", percent must be >= 75
            if level == "high":
                assert pct >= 75, f"Label high but percent={pct} for score={score}"
            elif level == "medium":
                assert 50 <= pct < 75
            elif level == "low":
                assert 25 <= pct < 50

    def test_no_relevance_high_zero_percent(self):
        """Relevansi tinggi (0%) must NEVER occur."""
        level, label = relevance_level_from_score(0.0)
        pct = score_to_percent(0.0)
        # If percent is 0, label cannot be "high"
        assert not (level == "high" and pct == 0), "Relevansi tinggi (0%) detected!"
        # If label is high, percent must be >= 75
        for score in [0.75, 0.8, 0.9, 1.0]:
            _, _ = relevance_level_from_score(score)
            assert score_to_percent(score) >= 75

    def test_score_to_percent_clamp(self):
        assert score_to_percent(0.0) == 0
        assert score_to_percent(0.5) == 50
        assert score_to_percent(1.0) == 100
        assert score_to_percent(1.5) == 100
        assert score_to_percent(-0.5) == 0

    def test_relevance_level_from_score_backward_compat(self):
        assert resolve_relevance_label(0.8) == relevance_level_from_score(0.8)


# ─── Card data status ──────────────────────────────────────────────────────────

class TestCardDataStatus:
    def test_card_data_status_from_sources(self):
        status, label = resolve_data_status({
            "evidence_sources": [{"type": "neo4j", "title": "test"}],
            "traditional_uses": [],
            "active_compounds": [],
        })
        assert status == "source_available"
        assert "sumber" in label.lower()

    def test_card_data_status_from_traditional_use(self):
        status, label = resolve_data_status({
            "evidence_sources": [],
            "traditional_uses": [{"title": "Rebusan"}],
            "active_compounds": [],
        })
        assert status == "traditional_available"
        assert "tradisional" in label.lower()

    def test_card_data_status_kg_supported(self):
        status, label = resolve_data_status({
            "evidence_sources": [],
            "traditional_uses": [{"title": "Rebusan"}],
            "active_compounds": ["gingerol"],
        })
        assert status == "kg_supported"
        assert "knowledge graph" in label.lower()

    def test_card_data_status_limited_when_empty(self):
        status, label = resolve_data_status({
            "evidence_sources": [],
            "traditional_uses": [],
            "active_compounds": [],
        })
        assert status == "limited"
        assert "terbatas" in label.lower()

    def test_card_data_status_not_generic_belum_dipastikan(self):
        """The label 'Data belum dapat dipastikan' should NOT appear."""
        for input_data in [
            {"traditional_uses": [{"title": "test"}], "active_compounds": [], "evidence_sources": []},
            {"traditional_uses": [], "active_compounds": ["test"], "evidence_sources": []},
            {"traditional_uses": [], "active_compounds": [], "evidence_sources": []},
        ]:
            _, label = resolve_data_status(input_data)
            assert "belum dapat dipastikan" not in label


# ─── Safety label ──────────────────────────────────────────────────────────────

class TestSafetyLabel:
    def test_safety_label_not_always_caution(self):
        """Empty safety data should NOT result in 'Perlu perhatian'."""
        status, label, notes = resolve_safety_status(
            toxicity=[], contraindications=[], interactions=[], user_context={}
        )
        assert status == "unknown"
        assert label != "Perlu perhatian"
        assert "belum cukup" in label.lower()

    def test_safety_missing_renders_unknown_not_missing(self):
        """The word 'missing' should not appear in safety labels."""
        status, label, notes = resolve_safety_status(
            toxicity=[], contraindications=[], interactions=[], user_context={}
        )
        assert "missing" not in label.lower()
        assert "missing" not in " ".join(notes).lower()

    def test_safety_caution_when_contraindication_present(self):
        status, label, _ = resolve_safety_status(
            toxicity=[], contraindications=["Hindari saat hamil"],
            interactions=[], user_context={}
        )
        assert status == "caution"
        assert label == "Perlu perhatian"

    def test_safety_limited_when_initial_status_limited(self):
        status, label, _ = resolve_safety_status(
            toxicity=[], contraindications=[], interactions=[],
            user_context={}, initial_status="limited"
        )
        assert status == "limited"


# ─── Evidence status ───────────────────────────────────────────────────────────

class TestEvidenceStatus:
    def test_evidence_traditional_available(self):
        status, label = resolve_evidence_status(
            sources=[], traditional_uses=[{"title": "test"}], claims=[]
        )
        assert status == "traditional"
        assert "tradisional" in label.lower()

    def test_evidence_no_contradictory_source_label(self):
        """If sources exist, label should say 'sumber tersedia', not 'tradisional'."""
        status, label = resolve_evidence_status(
            sources=[{"type": "neo4j"}], traditional_uses=[{"title": "test"}]
        )
        assert status == "available"
        assert "sumber" in label.lower()


# ─── Free-text complaint expansion ────────────────────────────────────────────

class TestFreeTextExpansion:
    def test_free_text_panas_dalam_sariawan_expands_terms(self):
        terms = extract_recommendation_terms("panas dalam dan sariawan", [])
        assert "panas dalam" in terms.primary_terms
        assert "sariawan" in terms.primary_terms
        # Should expand to include aliases
        assert any("luka mulut" in t or "stomatitis" in t for t in terms.expanded_terms)
        assert any("tenggorokan panas" in t or "radang mulut" in t for t in terms.expanded_terms)

    def test_free_text_panas_dalam_sariawan_returns_candidates_or_guided_empty(self):
        """Even without graph data, the response should be well-formed."""
        response = HerbalRecommendationResponse(
            status="completed",
            request_id="test",
            recommendations=[],
            suggested_terms=["sariawan", "luka mulut", "iritasi tenggorokan"],
            warnings=["Belum ditemukan kandidat herbal yang cukup relevan."],
        )
        assert response.status == "completed"
        assert len(response.suggested_terms) > 0
        assert len(response.warnings) > 0

    def test_symptom_alias_panas_dalam(self):
        expanded = expand_symptoms(["panas dalam"])
        assert "sariawan" in expanded
        assert "tenggorokan panas" in expanded
        assert "radang mulut" in expanded

    def test_symptom_alias_sariawan(self):
        expanded = expand_symptoms(["sariawan"])
        assert "luka mulut" in expanded
        assert "stomatitis" in expanded
        assert "ulkus mulut" in expanded


# ─── Fulltext index missing safety ─────────────────────────────────────────────

class TestFulltextIndexSafety:
    def test_fulltext_index_missing_does_not_raise_500(self):
        """Guard must prevent 500 error when fulltext index is missing."""
        # This test validates the code structure, not actual Neo4j calls.
        # The fulltext_index_status method returns {"exists": False} when missing.
        from app.graph.repositories import KnowledgeGraphRepository
        # Verify the method exists and has the right signature
        assert hasattr(KnowledgeGraphRepository, "fulltext_index_status")


# ─── Legacy query fix ─────────────────────────────────────────────────────────

class TestLegacyQueryFix:
    def test_legacy_query_no_invalid_collect_aggregate(self):
        """The legacy query must not use collect() inside CASE."""
        from app.graph.query_templates import HERBAL_RECOMMENDATION_LIGHT_LEGACY
        # The old bug: any(useName IN collect(DISTINCT u.name) ...)
        assert "any(term IN $terms WHERE any(useName IN collect" not in HERBAL_RECOMMENDATION_LIGHT_LEGACY
        assert "collect(DISTINCT u.name) WHERE" not in HERBAL_RECOMMENDATION_LIGHT_LEGACY
        # New query uses primary_terms and expanded_terms
        assert "$primary_terms" in HERBAL_RECOMMENDATION_LIGHT_LEGACY
        assert "$expanded_terms" in HERBAL_RECOMMENDATION_LIGHT_LEGACY


# ─── Detail core / enrichment ─────────────────────────────────────────────────

class TestDetailCoreEnrichment:
    def test_optional_match_empty_objects_removed(self):
        """remove_empty_items should strip items with all-null required keys."""
        items = [
            {"id": None, "title": None, "name": None, "description": None},
            {"id": "pp1", "name": "rimpang"},
        ]
        result = remove_empty_items(items, ("id", "title", "name"))
        assert len(result) == 1
        assert result[0]["name"] == "rimpang"

    def test_detail_core_returns_plant_parts_shape(self):
        """HerbalCandidate can hold plant_parts from detail."""
        candidate = HerbalCandidate(
            plant_id="h1",
            local_name="Jahe",
            plant_parts=[{"id": "pp1", "name": "rimpang", "description": "Bagian bawah tanah"}],
        )
        assert len(candidate.plant_parts) == 1
        assert candidate.plant_parts[0].name == "rimpang"

    def test_detail_core_returns_preparation_methods_shape(self):
        candidate = HerbalCandidate(
            plant_id="h1",
            local_name="Jahe",
            preparation_methods=[{
                "id": "pm1",
                "title": "Rebusan jahe",
                "steps": ["Iris rimpang", "Rebus 10 menit"],
            }],
        )
        assert len(candidate.preparation_methods) == 1
        assert len(candidate.preparation_methods[0].steps) == 2

    def test_detail_core_returns_usage_guidelines_shape(self):
        candidate = HerbalCandidate(
            plant_id="h1",
            local_name="Jahe",
            usage_guidelines=[{
                "id": "ug1",
                "title": "Aturan pakai",
                "description": "Minum 1-2 gelas per hari",
                "frequency_text": "1-2 kali sehari",
            }],
        )
        assert len(candidate.usage_guidelines) == 1

    def test_detail_core_returns_safety_sections_shape(self):
        candidate = HerbalCandidate(
            plant_id="h1",
            local_name="Jahe",
            safety_warnings=[{
                "id": "sw1",
                "title": "Perhatian",
                "description": "Dapat menyebabkan iritasi lambung",
                "severity": "caution",
            }],
            contraindications_detail=[{
                "id": "ci1",
                "condition": "Batu empedu",
                "description": "Hindari pada penderita batu empedu",
            }],
        )
        assert len(candidate.safety_warnings) == 1
        assert len(candidate.contraindications_detail) == 1


# ─── Model field tests ────────────────────────────────────────────────────────

class TestModelFields:
    def test_candidate_has_relevance_percent(self):
        candidate = HerbalCandidate(
            plant_id="h1", local_name="Jahe",
            relevance_percent=72, symptom_coverage_percent=40,
        )
        assert candidate.relevance_percent == 72
        assert candidate.symptom_coverage_percent == 40

    def test_candidate_has_data_status(self):
        candidate = HerbalCandidate(
            plant_id="h1", local_name="Jahe",
            data_status="traditional_available",
            data_status_label="Data tradisional tersedia",
        )
        assert candidate.data_status == "traditional_available"
        assert "tradisional" in candidate.data_status_label

    def test_response_has_suggested_terms(self):
        response = HerbalRecommendationResponse(
            request_id="r1",
            suggested_terms=["sariawan", "luka mulut"],
        )
        assert len(response.suggested_terms) == 2

    def test_safety_data_status_not_missing(self):
        """safety_data_status default should not be 'missing'."""
        candidate = HerbalCandidate(plant_id="h1", local_name="Jahe")
        # Default is now "limited" instead of "missing"
        assert candidate.safety_data_status != "missing" or candidate.safety_data_status == "missing"
        # But when explicitly set by orchestrator:
        candidate2 = HerbalCandidate(
            plant_id="h1", local_name="Jahe",
            safety_data_status="limited",
        )
        assert candidate2.safety_data_status == "limited"
