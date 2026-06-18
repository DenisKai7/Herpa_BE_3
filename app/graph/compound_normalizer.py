import re
from typing import Any

from pydantic import BaseModel


class NormalizedCompound(BaseModel):
    display_name: str
    normalized_name: str
    pubchem_cid: str | None = None
    iupac: str | None = None
    molecular_formula: str | None = None
    compound_class: str | None = None
    category: str = "unknown"
    component_kind: str = "unknown"


_IUPAC_ALIASES = {
    "2_(3,4_dihydroxyphenyl)_3,5,7_trihydroxy_4h_chromen_4_one": "quercetin",
    "3,5,7_trihydroxy_2_(4_hydroxyphenyl)_4h_chromen_4_one": "kaempferol",
}

_NUTRIENT_TERMS = {
    "vitamin": "vitamin",
    "asam askorbat": "vitamin",
    "retinol": "vitamin",
    "kalsium": "mineral",
    "calcium": "mineral",
    "zat besi": "mineral",
    "iron": "mineral",
    "kalium": "mineral",
    "potassium": "mineral",
    "protein": "macronutrient",
    "karbohidrat": "macronutrient",
    "lemak": "macronutrient",
}

_AMINO_ACIDS = ("alanine", "arginine", "glycine", "leucine", "lysine", "valine", "asam amino")
_PHYTO_CLASSES = {
    "flavonoid": ("flavonoid",),
    "phenolic_acid": ("phenolic acid", "asam fenolat", "klorogenat"),
    "terpenoid": ("terpenoid", "terpene"),
    "alkaloid": ("alkaloid",),
    "saponin": ("saponin",),
    "glucosinolate": ("glucosinolate", "glukosinolat"),
    "isothiocyanate": ("isothiocyanate", "isothiosianat"),
    "other_phytochemical": ("phenolic", "fenolat", "polifenol"),
}


class CompoundNormalizer:
    @staticmethod
    def normalize_name(name: str) -> str:
        text = str(name or "").strip().lower()
        text = re.sub(r"[‐-―−–—]", "-", text)
        text = re.sub(r"\b\d+(?:[.,]\d+)?\s*%\b", "", text)
        text = re.sub(r"\([^)]*(?:%|mg|g|ppm|µg|ug)[^)]*\)", "", text)
        text = re.sub(r"\b(senyawa|compound|kandungan|aktif)\s*[:\-]\s*", "", text)
        text = re.sub(r"[^a-z0-9α-ω,+()]+", "_", text)
        text = re.sub(r"_+", "_", text)
        return text.strip("_")

    @staticmethod
    def component_kind(name: str, compound_class: str | None = None) -> str:
        return CompoundNormalizer.category(name, compound_class)

    @staticmethod
    def category(name: str, compound_class: str | None = None) -> str:
        joined = f"{name} {compound_class or ''}".lower()
        for term, kind in _NUTRIENT_TERMS.items():
            if term in joined:
                return kind
        if any(term in joined for term in _AMINO_ACIDS):
            return "amino_acid"
        for category, terms in _PHYTO_CLASSES.items():
            if any(term in joined for term in terms):
                return category
        return "unknown"

    @staticmethod
    def is_iupac_like(name: str) -> bool:
        text = str(name or "").lower()
        return bool(re.search(r"\d.*(hydroxy|phenyl|chromen|one|acid|methyl|ethyl|oxo)", text))

    @classmethod
    def normalize_compound(cls, item: dict[str, Any]) -> NormalizedCompound | None:
        raw_name = str(item.get("name") or item.get("display_name") or "").strip()
        if not raw_name:
            return None
        norm = cls.normalize_name(raw_name)
        alias = _IUPAC_ALIASES.get(norm)
        iupac = item.get("iupac") or None
        display = alias.title() if alias else raw_name
        if cls.is_iupac_like(raw_name) and not iupac:
            iupac = raw_name
        if alias:
            display = {"quercetin": "Quercetin", "kaempferol": "Kaempferol"}.get(alias, alias.title())
            norm = alias
        compound_class = item.get("compound_class") or item.get("compoundClass")
        cid = item.get("pubchem_cid") or item.get("pubchemCID")
        cid_text = str(cid).strip() if cid not in (None, "") else None
        category = cls.category(display, compound_class)
        return NormalizedCompound(
            display_name=display,
            normalized_name=norm,
            pubchem_cid=cid_text if cid_text and cid_text.lower() not in {"none", "null"} else None,
            iupac=str(iupac).strip() if iupac else None,
            molecular_formula=item.get("molecular_formula") or item.get("molecularFormula") or item.get("formula"),
            compound_class=compound_class,
            category=category,
            component_kind=category,
        )

    @classmethod
    def deduplicate(cls, compounds: list[dict[str, Any]], persona: str = "") -> list[dict[str, Any]]:
        seen: set[str] = set()
        by_key: dict[str, dict[str, Any]] = {}
        for item in compounds:
            if not isinstance(item, dict):
                continue
            normalized = cls.normalize_compound(item)
            if normalized is None:
                continue
            key = f"cid:{normalized.pubchem_cid}" if normalized.pubchem_cid else f"name:{normalized.normalized_name}"
            alias_key = f"name:{normalized.normalized_name}"
            if key in seen or alias_key in seen:
                current = by_key.get(key) or by_key.get(alias_key)
                if current and persona != "umum" and not current.get("iupac") and normalized.iupac:
                    current["iupac"] = normalized.iupac
                continue
            seen.add(key)
            seen.add(alias_key)
            data = normalized.model_dump()
            data["name"] = normalized.display_name
            if persona == "umum":
                data["iupac"] = None
            by_key[key] = data
        return list(by_key.values())

    @classmethod
    def prioritize_active(cls, compounds: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
        active_categories = {
            "flavonoid",
            "phenolic_acid",
            "terpenoid",
            "alkaloid",
            "saponin",
            "glucosinolate",
            "isothiocyanate",
            "other_phytochemical",
        }
        phyto = [c for c in compounds if c.get("category") in active_categories or c.get("component_kind") in active_categories]
        other = [c for c in compounds if c.get("category") not in {"vitamin", "mineral", "macronutrient", "amino_acid", *active_categories}]
        nutrients = [c for c in compounds if c.get("category") in {"vitamin", "mineral", "macronutrient", "amino_acid"}]
        return (phyto + other + nutrients)[:limit]


class_name = CompoundNormalizer
