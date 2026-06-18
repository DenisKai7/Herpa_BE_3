from typing import Any

from app.core.constants import Persona
from app.graph.compound_normalizer import CompoundNormalizer
from app.services.ai.grounding_models import GroundedSource


def format_compound_list(
    *,
    herb: dict[str, Any],
    compounds: list[dict[str, Any]],
    sources: list[GroundedSource],
    persona: Persona,
) -> tuple[str, int]:
    normalized = CompoundNormalizer.prioritize_active(
        CompoundNormalizer.deduplicate(compounds, persona=persona.value), limit=10
    )
    active = [c for c in normalized if c.get("category") not in {"vitamin", "mineral", "macronutrient", "amino_acid"}]
    nutrients = [c for c in normalized if c.get("category") in {"vitamin", "mineral", "macronutrient", "amino_acid"}]
    shown = (active or normalized)[:10]
    common = _common_name(herb)
    scientific = _scientific_name(herb)
    sci = f" ({scientific})" if scientific else ""

    if persona == Persona.PENELITI:
        lines = [f"Profil senyawa utama {common}{sci}:", ""]
        for item in shown:
            meta = [str(item.get("compound_class"))] if item.get("compound_class") else []
            if item.get("pubchem_cid"):
                meta.append(f"PubChem CID {item['pubchem_cid']}")
            if item.get("molecular_formula"):
                meta.append(str(item["molecular_formula"]))
            if item.get("iupac"):
                meta.append(f"IUPAC: {item['iupac']}")
            lines.append(f"• {item.get('display_name') or item.get('name')}" + (f" — {'; '.join(meta)}" if meta else ""))
    elif persona == Persona.PELAJAR:
        lines = [f"Senyawa aktif utama pada {common}{sci}:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines += ["", _group_sentence(shown), "Fitokimia adalah senyawa khas tumbuhan; vitamin dan mineral termasuk nutrisi."]
    elif persona == Persona.TENAGA_MEDIS:
        lines = [f"Komponen fitokimia utama {common}{sci}:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines += ["", _group_sentence(shown), "Data ini bukan dasar dosis klinis atau rekomendasi terapi pasien."]
    else:
        lines = [f"Senyawa utama yang tercatat pada {common}{sci} antara lain:", ""]
        lines.extend(f"• {item.get('display_name') or item.get('name')}" for item in shown[:8])
        lines += ["", _group_sentence(shown), "Kandungannya dapat berbeda menurut bagian tanaman dan cara pengolahannya."]
        if nutrients:
            lines.append("Selain fitokimia, data juga dapat mencatat vitamin/mineral sebagai komponen nutrisi, bukan senyawa aktif utama.")
    lines += ["", _format_sources(sources)]
    return "\n".join(lines), len(shown)


def format_herb_identity(*, herb: dict[str, Any], sources: list[GroundedSource], persona: Persona) -> str:
    lines = [f"Identitas tanaman: {_common_name(herb)}."]
    scientific = _scientific_name(herb)
    if scientific:
        lines.append(f"Nama ilmiah: {scientific}.")
    simplisia = herb.get("simplisia_name") or herb.get("simplisiaName")
    if simplisia:
        lines.append(f"Nama simplisia: {simplisia}.")
    lines.append(_format_sources(sources))
    return "\n".join(lines)


def format_therapeutic_uses(
    *, herb: dict[str, Any], uses: list[dict[str, Any]], sources: list[GroundedSource], persona: Persona
) -> str:
    lines = [f"Kegunaan yang tercatat untuk {_common_name(herb)}:", ""]
    for use in uses[:8]:
        name = use.get("name") if isinstance(use, dict) else str(use)
        if name:
            lines.append(f"• {name}")
    lines += ["", "Daftar ini mengikuti knowledge graph, bukan anjuran dosis.", _format_sources(sources)]
    return "\n".join(lines)


def _common_name(herb: dict[str, Any]) -> str:
    return str(herb.get("common_name") or herb.get("commonName") or herb.get("name") or "tanaman").strip()


def _scientific_name(herb: dict[str, Any]) -> str:
    return str(
        herb.get("scientific_name")
        or herb.get("canonicalScientificName")
        or herb.get("canonical_scientific_name")
        or herb.get("latinName")
        or ""
    ).strip()


def _group_sentence(compounds: list[dict[str, Any]]) -> str:
    classes: list[str] = []
    for compound in compounds:
        cls = compound.get("compound_class")
        if cls and str(cls).lower() not in [c.lower() for c in classes]:
            classes.append(str(cls))
    if not classes:
        return "Senyawa tersebut terutama termasuk kelompok fitokimia bila kelasnya tersedia pada data."
    return "Senyawa tersebut terutama termasuk kelompok " + ", ".join(classes[:4]) + "."


def _format_sources(sources: list[GroundedSource]) -> str:
    if not sources:
        return "Sumber data: knowledge graph HERPA."
    return "Sumber data: " + "; ".join(source.title for source in sources[:3]) + "."
