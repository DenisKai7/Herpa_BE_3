import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.constants import Persona
from app.graph.compound_normalizer import CompoundNormalizer
from app.models.common import SourceReference
from app.services.ai.grounding_models import DataCoverage, GroundedSource
from app.services.ai.persona_formatter import format_compound_list, format_herb_identity, format_therapeutic_uses
from app.services.ai.query_intent import QueryIntent


class DirectAnswerResult(BaseModel):
    handled: bool
    answer: str | None = None
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    grounding_status: str = "insufficient"
    data_coverage: dict[str, bool] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)
    latency_ms: int = 0
    compound_count: int = 0
    coverage: DataCoverage = DataCoverage()


HerbContext = dict[str, Any]


def _source_title(source: dict[str, Any]) -> str:
    return str(
        source.get("title")
        or source.get("name")
        or source.get("source_name")
        or source.get("category")
        or "Knowledge graph"
    ).strip()


def _source_references(sources: list[GroundedSource]) -> list[SourceReference]:
    return [
        SourceReference(
            type=source.source_type,
            source_id=source.identifier or source.title,
            title=source.title,
            identifier=source.identifier,
            year=source.year,
            url=source.url,
        )
        for source in sources
    ]


def normalize_sources(sources: list[dict[str, Any]]) -> list[GroundedSource]:
    normalized: list[GroundedSource] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        title = _source_title(source)
        if not title:
            continue
        identifier = source.get("identifier") or source.get("doi") or source.get("pmid") or source.get("source_id")
        year = source.get("year")
        try:
            year = int(str(year)) if year not in (None, "") else None
        except (TypeError, ValueError):
            year = None
        normalized.append(
            GroundedSource(
                source_type=str(source.get("source_type") or source.get("type") or "neo4j"),
                title=title,
                identifier=str(identifier) if identifier not in (None, "") else None,
                year=year,
                url=source.get("url"),
            )
        )
    return normalized


def _coverage(graph_context: HerbContext) -> DataCoverage:
    return DataCoverage(
        herb_found=bool(graph_context.get("herb")),
        compounds_available=bool(graph_context.get("compounds")),
        uses_available=bool(graph_context.get("therapeutic_uses")),
        sources_available=bool(graph_context.get("sources")),
        toxicity_available=bool(graph_context.get("toxicity")),
        clinical_data_available=bool(graph_context.get("clinical_data")),
    )


def _scientific_name(herb: dict[str, Any]) -> str:
    return str(
        herb.get("scientific_name")
        or herb.get("canonicalScientificName")
        or herb.get("canonical_scientific_name")
        or herb.get("latinName")
        or herb.get("latin_name")
        or ""
    ).strip()


def _common_name(herb: dict[str, Any]) -> str:
    return str(herb.get("common_name") or herb.get("commonName") or herb.get("name") or herb.get("local_name") or "tanaman").strip()


def _format_sources(sources: list[GroundedSource]) -> str:
    if not sources:
        return "Sumber data: knowledge graph HERPA."
    labels = []
    for source in sources[:3]:
        detail = source.title
        if source.year:
            detail = f"{detail} ({source.year})"
        if source.identifier:
            detail = f"{detail}, {source.identifier}"
        labels.append(detail)
    return "Sumber data: " + "; ".join(labels) + "."


def _specific_warnings(coverage: DataCoverage, intent: QueryIntent) -> list[str]:
    warnings: list[str] = []
    if not coverage.herb_found:
        warnings.append("Data tanaman belum ditemukan pada knowledge graph.")
    if intent == QueryIntent.COMPOUND_LIST and not coverage.compounds_available:
        warnings.append("Data kandungan senyawa belum tersedia pada sumber yang digunakan.")
    if intent == QueryIntent.THERAPEUTIC_USE_LIST and not coverage.uses_available:
        warnings.append("Data kegunaan terapeutik belum tersedia pada sumber yang digunakan.")
    if not coverage.sources_available:
        warnings.append("Metadata sumber khusus belum tersedia; jawaban dibatasi pada data knowledge graph.")
    return warnings


def _compound_group_sentence(compounds: list[dict[str, Any]]) -> str:
    classes: list[str] = []
    for compound in compounds:
        cls = compound.get("compound_class")
        if cls and str(cls).strip().lower() not in [c.lower() for c in classes]:
            classes.append(str(cls).strip())
    if classes:
        return "Senyawa-senyawa tersebut terutama termasuk kelompok " + ", ".join(classes[:4]) + "."
    return "Senyawa-senyawa tersebut terutama termasuk kelompok flavonoid, asam fenolat, dan senyawa sulfur bila kelasnya tersedia pada data."


def _compound_answer(graph_context: HerbContext, persona: Persona, sources: list[GroundedSource]) -> tuple[str, int]:
    herb = graph_context.get("herb") or {}
    common = _common_name(herb)
    scientific = _scientific_name(herb)
    raw_compounds = graph_context.get("compounds") or []
    compounds = CompoundNormalizer.deduplicate(raw_compounds, persona=persona.value)
    compounds = CompoundNormalizer.prioritize_active(compounds, limit=10)
    active = [c for c in compounds if c.get("component_kind") not in {"vitamin", "mineral", "macronutrient", "amino_acid"}]
    nutrients = [c for c in compounds if c.get("component_kind") in {"vitamin", "mineral", "macronutrient", "amino_acid"}]
    shown = (active or compounds)[:10]
    sci = f" ({scientific})" if scientific else ""

    if persona == Persona.PENELITI:
        lines = [f"Profil senyawa utama {common}{sci}:", ""]
        for item in shown:
            meta = []
            if item.get("compound_class"):
                meta.append(str(item["compound_class"]))
            if item.get("pubchem_cid"):
                meta.append(f"PubChem CID {item['pubchem_cid']}")
            if item.get("molecular_formula"):
                meta.append(str(item["molecular_formula"]))
            if item.get("iupac"):
                meta.append(f"IUPAC: {item['iupac']}")
            lines.append(f"• {item['display_name'] if 'display_name' in item else item.get('name')}" + (f" — {'; '.join(meta)}" if meta else ""))
        lines.extend(["", _format_sources(sources)])
        return "\n".join(lines), len(shown)

    if persona == Persona.PELAJAR:
        lines = [f"Senyawa aktif utama pada {common}{sci} yang tercatat antara lain:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines.extend(["", _compound_group_sentence(shown), "Fitokimia adalah senyawa tumbuhan yang dapat berperan sebagai penanda kandungan atau aktivitas biologis awal, tetapi bukan otomatis bukti klinis."])
    elif persona == Persona.TENAGA_MEDIS:
        lines = [f"Komponen fitokimia utama {common}{sci}:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines.extend(["", _compound_group_sentence(shown), "Data ini menjelaskan kandungan fitokimia, bukan dasar dosis atau terapi klinis. Gunakan data safety terpisah bila membahas pasien."])
    else:
        lines = [f"Senyawa utama yang tercatat pada {common}{sci} antara lain:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines.extend(["", _compound_group_sentence(shown), "Kandungan dapat berbeda bergantung pada bagian tanaman dan metode pengolahannya."])
        if nutrients:
            lines.append("Selain fitokimia, data tanaman juga dapat mencatat vitamin/mineral, tetapi itu komponen nutrisi, bukan senyawa aktif utama.")
    lines.extend(["", _format_sources(sources)])
    return "\n".join(lines), len(shown)


def _identity_answer(graph_context: HerbContext, persona: Persona, sources: list[GroundedSource]) -> str:
    herb = graph_context.get("herb") or {}
    common = _common_name(herb)
    scientific = _scientific_name(herb)
    simplisia = herb.get("simplisia_name") or herb.get("simplisiaName")
    lines = [f"Identitas tanaman: {common}."]
    if scientific:
        lines.append(f"Nama ilmiah: {scientific}.")
    if simplisia:
        lines.append(f"Nama simplisia: {simplisia}.")
    lines.append(_format_sources(sources))
    return "\n".join(lines)


def _uses_answer(graph_context: HerbContext, persona: Persona, sources: list[GroundedSource]) -> str:
    herb = graph_context.get("herb") or {}
    uses = graph_context.get("therapeutic_uses") or []
    common = _common_name(herb)
    lines = [f"Kegunaan yang tercatat untuk {common}:", ""]
    for use in uses[:8]:
        name = use.get("name") if isinstance(use, dict) else str(use)
        if name:
            lines.append(f"• {name}")
    lines.extend(["", "Daftar ini mengikuti data knowledge graph, bukan anjuran dosis atau pengganti konsultasi medis.", _format_sources(sources)])
    return "\n".join(lines)


async def build_direct_answer(
    *,
    query: str,
    intent: QueryIntent,
    persona: Persona,
    graph_context: HerbContext,
) -> DirectAnswerResult:
    started = time.perf_counter()
    coverage = _coverage(graph_context)
    warnings = _specific_warnings(coverage, intent)
    sources = normalize_sources(graph_context.get("sources") or [])
    source_refs = _source_references(sources)
    coverage_dict = coverage.model_dump()
    metadata = {
        "direct_answer_used": True,
        "model_calls": 0,
        "refinement_used": False,
        "retrieval_source": graph_context.get("retrieval_source", "neo4j"),
    }
    if not coverage.herb_found:
        return DirectAnswerResult(
            handled=False,
            answer=None,
            sources=source_refs,
            warnings=warnings,
            grounding_status="insufficient",
            data_coverage=coverage_dict,
            metadata=metadata,
            latency_ms=int((time.perf_counter() - started) * 1000),
            coverage=coverage,
        )

    compound_count = 0
    if intent == QueryIntent.COMPOUND_LIST and coverage.compounds_available:
        answer, compound_count = format_compound_list(
            herb=graph_context.get("herb") or {},
            compounds=graph_context.get("compounds") or [],
            sources=sources,
            persona=persona,
        )
    elif intent == QueryIntent.HERB_IDENTITY:
        answer = format_herb_identity(herb=graph_context.get("herb") or {}, sources=sources, persona=persona)
    elif intent == QueryIntent.THERAPEUTIC_USE_LIST and coverage.uses_available:
        answer = format_therapeutic_uses(
            herb=graph_context.get("herb") or {},
            uses=graph_context.get("therapeutic_uses") or [],
            sources=sources,
            persona=persona,
        )
    else:
        return DirectAnswerResult(
            handled=False,
            answer=None,
            sources=source_refs,
            warnings=warnings,
            grounding_status="insufficient",
            data_coverage=coverage_dict,
            metadata=metadata,
            latency_ms=int((time.perf_counter() - started) * 1000),
            coverage=coverage,
        )

    return DirectAnswerResult(
        handled=True,
        answer=answer,
        sources=source_refs,
        warnings=warnings,
        grounding_status="grounded" if coverage.sources_available else "partial",
        data_coverage=coverage_dict,
        metadata=metadata,
        latency_ms=int((time.perf_counter() - started) * 1000),
        compound_count=compound_count,
        coverage=coverage,
    )
