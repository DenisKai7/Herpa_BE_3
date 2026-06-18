from enum import StrEnum
import re

from pydantic import BaseModel


class QueryIntent(StrEnum):
    COMPOUND_LIST = "compound-list"
    HERB_IDENTITY = "herb-identity"
    THERAPEUTIC_USE_LIST = "therapeutic-use-list"
    SIMPLE_EXPLANATION = "simple-explanation"
    COMPARISON = "comparison"
    RESEARCH_ANALYSIS = "research-analysis"
    MEDICAL_SAFETY = "medical-safety"
    DOCUMENT_ANALYSIS = "document-analysis"
    GENERAL = "general"


class IntentResult(BaseModel):
    intent: QueryIntent
    confidence: float
    entities: list[str]
    normalized_query: str


_NORMALIZATIONS: tuple[tuple[str, str], ...] = (
    ("apa aja", "apa saja"),
    ("apa aj", "apa saja"),
    ("di dalam", "dalam"),
    ("didalam", "dalam"),
    ("kandungan apa", "kandungan"),
    ("senyawa aktifnya", "senyawa aktif"),
    ("senyawanya", "senyawa"),
    ("kandungannya", "kandungan"),
    ("aktifnya", "aktif"),
    ("manfaatnya", "manfaat"),
    ("khasiatnya", "khasiat"),
    ("nama latin", "nama ilmiah"),
)


def normalize_query_text(query: str) -> str:
    text = query.lower().strip()
    text = re.sub(r"[‐-―]", "-", text)
    text = re.sub(r"\s+", " ", text)
    for old, new in _NORMALIZATIONS:
        text = text.replace(old, new)
    return text.strip()


def _extract_entities(text: str) -> list[str]:
    stopwords = {"apa", "saja", "dalam", "di", "senyawa", "aktif", "kandungan", "kimia", "manfaat", "nama", "ilmiah"}
    return [token for token in re.findall(r"[a-zA-ZÀ-ÿ]{3,}", text) if token not in stopwords][:5]


def classify_intent(query: str) -> IntentResult:
    normalized = normalize_query_text(query)
    intent = classify_query_intent(query)
    confidence = 0.95 if intent != QueryIntent.GENERAL else 0.5
    return IntentResult(intent=intent, confidence=confidence, entities=_extract_entities(normalized), normalized_query=normalized)


def classify_query_intent(query: str) -> QueryIntent:
    text = normalize_query_text(query)

    if any(term in text for term in ("file", "dokumen", "pdf", "lampiran", "attachment", "unggahan")):
        return QueryIntent.DOCUMENT_ANALYSIS

    if any(
        term in text
        for term in (
            "interaksi obat",
            "kontraindikasi",
            "efek samping",
            "dosis",
            "ibu hamil",
            "menyusui",
            "toksik",
            "racun",
            "aman untuk",
            "bahaya",
        )
    ):
        return QueryIntent.MEDICAL_SAFETY

    if any(term in text for term in ("bandingkan", "perbandingan", " vs ", "versus", "lebih baik", "beda ")):
        return QueryIntent.COMPARISON

    if any(
        term in text
        for term in (
            "mekanisme",
            "molekuler",
            "hplc",
            "gc-ms",
            "gc ms",
            "farmakokinetik",
            "adme",
            "praklinik",
            "klinis",
            "metodologi",
            "ekstraksi",
            "analisis fitokimia",
            "bukti penelitian",
        )
    ):
        return QueryIntent.RESEARCH_ANALYSIS

    compound_terms = (
        "senyawa",
        "senyawa aktif",
        "kandungan kimia",
        "fitokimia",
        "metabolit sekunder",
        "komponen aktif",
        "zat aktif",
        "marker compound",
        "kandungan aktif",
    )
    if any(term in text for term in compound_terms):
        return QueryIntent.COMPOUND_LIST

    if any(term in text for term in ("nama ilmiah", "nama latin", "identitas", "spesies", "simplisia")):
        return QueryIntent.HERB_IDENTITY

    if any(term in text for term in ("manfaat", "khasiat", "kegunaan", "digunakan untuk", "indikasi")):
        return QueryIntent.THERAPEUTIC_USE_LIST

    if any(term in text for term in ("apa itu", "jelaskan", "pengertian")):
        return QueryIntent.SIMPLE_EXPLANATION

    return QueryIntent.GENERAL


DIRECT_ANSWER_INTENTS = {
    QueryIntent.COMPOUND_LIST,
    QueryIntent.HERB_IDENTITY,
    QueryIntent.THERAPEUTIC_USE_LIST,
}
