import math

from app.logic.recommendation_orchestrator import (
    build_recommendation_explanation,
    clamp_score,
    detect_cough_red_flags,
    resolve_evidence_status,
    resolve_relevance_label,
    resolve_safety_status,
)
from app.models.recommendation import HerbalCandidate, HerbalRecommendationResponse, RecommendationScore
from app.services.recommendation.symptom_aliases import expand_symptoms


def test_recommendation_score_never_nan():
    candidate = HerbalCandidate(local_name="Kencur", scientific_name="Kaempferia galanga L.", plant_id="h1")
    data = candidate.model_dump()

    assert not math.isnan(data["confidence"])
    assert not math.isnan(data["relevance_score"])
    assert not math.isnan(data["scores"]["confidence"])


def test_recommendation_confidence_is_clamped():
    assert clamp_score(float("nan")) == 0.0
    assert clamp_score(float("inf")) == 0.0
    assert clamp_score(-2) == 0.0
    assert clamp_score(2) == 1.0
    assert clamp_score(0.42) == 0.42


def test_empty_safety_data_maps_to_unknown_not_unsafe():
    status, label, notes = resolve_safety_status(
        toxicity=[], contraindications=[], interactions=[], user_context={}
    )

    assert status == "unknown"
    assert label == "Data keamanan belum cukup"
    assert notes


def test_empty_evidence_maps_to_unavailable():
    assert resolve_evidence_status([]) == ("unavailable", "Data bukti belum tersedia")


def test_relevance_label_low_medium_high():
    assert resolve_relevance_label(0.8) == ("high", "Relevansi tinggi")
    assert resolve_relevance_label(0.5) == ("medium", "Relevansi sedang")
    assert resolve_relevance_label(0.1) == ("low", "Relevansi rendah")
    assert resolve_relevance_label(0.0) == ("unknown", "Relevansi belum tersedia")


def test_recommendation_has_explanation():
    explanation, _ = build_recommendation_explanation(
        local_name="Kencur",
        symptoms=["batuk berdahak"],
        related_uses=["batuk"],
        confidence=0.42,
    )

    assert "Kencur" in explanation
    assert "diagnosis" not in explanation.lower()


def test_recommendation_has_match_reasons():
    _, reasons = build_recommendation_explanation(
        local_name="Kencur",
        symptoms=["batuk berdahak"],
        related_uses=["batuk"],
        confidence=0.42,
    )

    assert reasons
    assert any("Keluhan" in reason for reason in reasons)


def test_symptom_alias_expansion_for_batuk_berdahak():
    expanded = expand_symptoms(["batuk berdahak"])

    assert "batuk" in expanded
    assert "ekspektoran" in expanded
    assert "saluran pernapasan" in expanded


def test_symptom_alias_expansion_for_tenggorokan_gatal():
    expanded = expand_symptoms(["tenggorokan gatal"])

    assert "tenggorokan" in expanded
    assert "iritasi tenggorokan" in expanded
    assert "antiinflamasi" in expanded


def test_recommendation_response_uses_recommendations_primary():
    candidate = HerbalCandidate(local_name="Kencur", scientific_name="Kaempferia galanga L.", plant_id="h1")
    response = HerbalRecommendationResponse(request_id="r1", recommendations=[candidate])

    assert response.recommendations == [candidate]


def test_options_alias_matches_recommendations():
    candidate = HerbalCandidate(local_name="Kencur", scientific_name="Kaempferia galanga L.", plant_id="h1")
    response = HerbalRecommendationResponse(request_id="r1", recommendations=[candidate], options=[])

    assert response.options == response.recommendations


def test_low_confidence_candidate_label():
    level, label = resolve_relevance_label(0.19)

    assert level == "low"
    assert label == "Relevansi rendah"


def test_red_flag_detection_for_cough():
    red_flags = detect_cough_red_flags("batuk berdahak disertai sesak napas")

    assert "sesak napas" in red_flags


def test_no_diagnosis_or_dose_without_source():
    candidate = HerbalCandidate(
        local_name="Kencur",
        scientific_name="Kaempferia galanga L.",
        plant_id="h1",
        explanation="Kencur muncul sebagai kandidat awal, tetapi relevansinya masih rendah sehingga perlu verifikasi lebih lanjut.",
        scores=RecommendationScore(confidence=0.2),
    )

    text = candidate.model_dump_json().lower()
    assert "diagnosis" not in text
    assert "dosis" not in text
