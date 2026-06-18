from app.core.constants import Persona
from app.services.ai.complexity_analyzer import assess_complexity
from app.services.ai.query_intent import QueryIntent


def test_thinking_high_simple_uses_one_call():
    assessment = assess_complexity("senyawa dalam kelor apa saja?", Persona.UMUM, QueryIntent.COMPOUND_LIST)
    assert assessment.requires_refinement is False
    assert assessment.requires_pubmed is False
    assert assessment.requires_pubchem is False
    assert assessment.requires_protein_targets is False


def test_thinking_high_complex_can_refine():
    assessment = assess_complexity(
        "analisis mekanisme molekuler, bukti klinis, interaksi obat, dan ADME kelor",
        Persona.PENELITI,
        QueryIntent.RESEARCH_ANALYSIS,
    )
    assert assessment.requires_refinement is True
    assert assessment.requires_pubmed is True
    assert assessment.requires_pubchem is True
    assert assessment.requires_protein_targets is True
    assert assessment.requires_safety_review is True
