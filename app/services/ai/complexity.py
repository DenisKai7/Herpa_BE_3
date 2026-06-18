from pydantic import BaseModel

from app.core.constants import Persona


class ComplexityAssessment(BaseModel):
    score: int
    requires_refinement: bool
    requires_pubmed: bool
    requires_pubchem: bool
    requires_protein_targets: bool
    requires_safety_review: bool
    reasons: list[str]


def assess_complexity(query: str, persona: Persona) -> ComplexityAssessment:
    reasons = []
    score = 0
    requires_refinement = False
    requires_pubmed = False
    requires_pubchem = False
    requires_protein_targets = False
    requires_safety_review = False

    lower = query.lower()

    # Safety-critical terms
    safety_keywords = [
        "dosis",
        "interaksi",
        "kontraindikasi",
        "efek samping",
        "aman",
        "bahaya",
        "toksik",
        "racun",
        "ibu hamil",
        "menyusui",
        "ginjal",
        "hati",
        "liver",
    ]
    matched_safety = [w for w in safety_keywords if w in lower]
    if matched_safety:
        requires_safety_review = True
        score += 2
        reasons.append(f"Mendeteksi kata kunci keamanan: {', '.join(matched_safety)}")

    # Complex chemical/mechanistic terms
    mech_keywords = [
        "mekanisme",
        "molekuler",
        "reseptor",
        "protein",
        "enzim",
        "jalur",
        "afinitas",
        "docking",
        "adme",
        "farmakokinetik",
        "farmakodinamik",
        "ikatan",
    ]
    matched_mech = [w for w in mech_keywords if w in lower]
    if matched_mech:
        requires_protein_targets = True
        requires_pubchem = True
        score += 2
        reasons.append(f"Mendeteksi kata kunci mekanisme/kimia: {', '.join(matched_mech)}")

    # Research-oriented terms
    research_keywords = [
        "uji",
        "klinis",
        "jurnal",
        "penelitian",
        "bukti",
        "literatur",
        "artikel",
        "metodologi",
        "in vivo",
        "in vitro",
        "praklinik",
    ]
    matched_res = [w for w in research_keywords if w in lower]
    if matched_res:
        requires_pubmed = True
        score += 2
        reasons.append(f"Mendeteksi kata kunci penelitian: {', '.join(matched_res)}")

    # Comparison / synthesis indicators
    comparison_keywords = [
        "bandingkan",
        "beda",
        "vs",
        "versus",
        "lebih baik",
        "mana yang",
        "kombinasi",
        "campuran",
    ]
    matched_comp = [w for w in comparison_keywords if w in lower]
    if matched_comp:
        requires_refinement = True
        score += 1
        reasons.append(f"Mendeteksi indikator perbandingan/sintesis: {', '.join(matched_comp)}")

    # Persona based logic
    if persona == Persona.TENAGA_MEDIS:
        requires_safety_review = True
        requires_refinement = True
        score += 2
        reasons.append("Persona Tenaga Medis memerlukan safety review dan refinement wajib.")
    elif persona == Persona.PENELITI:
        requires_pubmed = True
        requires_refinement = True
        score += 2
        reasons.append("Persona Peneliti memerlukan PubMed dan refinement wajib.")

    # High complexity threshold
    if score >= 3:
        requires_refinement = True

    return ComplexityAssessment(
        score=score,
        requires_refinement=requires_refinement,
        requires_pubmed=requires_pubmed,
        requires_pubchem=requires_pubchem,
        requires_protein_targets=requires_protein_targets,
        requires_safety_review=requires_safety_review,
        reasons=reasons,
    )
