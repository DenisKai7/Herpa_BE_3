from pydantic import BaseModel

from app.core.constants import Persona
from app.services.ai.query_intent import QueryIntent, classify_query_intent, normalize_query_text


class ComplexityAssessment(BaseModel):
    score: int
    requires_refinement: bool
    requires_pubmed: bool
    requires_pubchem: bool
    requires_protein_targets: bool
    requires_safety_review: bool
    reasons: list[str]


_SIMPLE_INTENTS = {
    QueryIntent.COMPOUND_LIST,
    QueryIntent.HERB_IDENTITY,
    QueryIntent.THERAPEUTIC_USE_LIST,
}


def assess_complexity(query: str, persona: Persona, intent: QueryIntent | None = None) -> ComplexityAssessment:
    intent = intent or classify_query_intent(query)
    text = normalize_query_text(query)
    reasons: list[str] = []
    score = 1
    requires_refinement = False
    requires_pubmed = False
    requires_pubchem = False
    requires_protein_targets = False
    requires_safety_review = False

    if intent in _SIMPLE_INTENTS:
        return ComplexityAssessment(
            score=1,
            requires_refinement=False,
            requires_pubmed=False,
            requires_pubchem=False,
            requires_protein_targets=False,
            requires_safety_review=False,
            reasons=[f"Intent sederhana: {intent.value}"],
        )

    if intent == QueryIntent.COMPARISON:
        score += 2
        requires_refinement = True
        reasons.append("Pertanyaan perbandingan memerlukan sintesis.")

    if intent == QueryIntent.MEDICAL_SAFETY:
        score += 3
        requires_refinement = True
        requires_pubmed = True
        requires_safety_review = True
        reasons.append("Pertanyaan safety medis memerlukan pemeriksaan bukti.")

    if intent == QueryIntent.RESEARCH_ANALYSIS:
        score += 3
        requires_refinement = True
        requires_pubmed = True
        reasons.append("Pertanyaan riset memerlukan bukti eksternal.")

    pubchem_terms = ("pubchem", "cid", "iupac", "formula", "struktur", "kimia", "adme", "farmakokinetik")
    if any(term in text for term in pubchem_terms):
        score += 1
        requires_pubchem = True
        reasons.append("Butuh metadata kimia/PubChem.")

    target_terms = ("mekanisme", "molekuler", "protein", "reseptor", "enzim", "jalur", "docking", "target")
    if any(term in text for term in target_terms):
        score += 2
        requires_protein_targets = True
        requires_pubchem = True
        requires_refinement = True
        reasons.append("Butuh target protein/mekanisme.")

    safety_terms = ("interaksi obat", "kontraindikasi", "dosis", "efek samping", "ibu hamil", "menyusui")
    if any(term in text for term in safety_terms):
        score += 2
        requires_safety_review = True
        requires_pubmed = True
        requires_refinement = True
        reasons.append("Butuh tinjauan keamanan.")

    if persona == Persona.TENAGA_MEDIS and requires_safety_review:
        score += 1
        reasons.append("Persona tenaga medis + safety.")
    if persona == Persona.PENELITI and intent in {QueryIntent.RESEARCH_ANALYSIS, QueryIntent.COMPARISON}:
        score += 1
        requires_pubmed = True
        reasons.append("Persona peneliti pada pertanyaan kompleks.")

    return ComplexityAssessment(
        score=min(score, 10),
        requires_refinement=requires_refinement or score >= 4,
        requires_pubmed=requires_pubmed,
        requires_pubchem=requires_pubchem,
        requires_protein_targets=requires_protein_targets,
        requires_safety_review=requires_safety_review,
        reasons=reasons or ["Pertanyaan umum."],
    )
