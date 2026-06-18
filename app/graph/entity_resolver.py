import re

from app.models.graph import GraphEntity

RESOLVE_HERB_ENTITY = """
MATCH (h:Herb)
WITH h,
CASE
    WHEN toLower(coalesce(h.commonName, '')) = toLower($entity) THEN 1.0
    WHEN toLower(coalesce(h.canonicalScientificName, '')) = toLower($entity) THEN 0.98
    WHEN toLower(coalesce(h.latinName, '')) = toLower($entity) THEN 0.95
    WHEN any(localName IN coalesce(h.localNames, []) WHERE toLower(localName) = toLower($entity)) THEN 0.92
    WHEN toLower(coalesce(h.commonName, '')) CONTAINS toLower($entity) THEN 0.80
    WHEN any(localName IN coalesce(h.localNames, []) WHERE toLower(localName) CONTAINS toLower($entity)) THEN 0.75
    ELSE 0.0
END AS score
WHERE score > 0
RETURN {
    entity_id: h.id,
    entity_type: 'Herb',
    local_name: h.commonName,
    scientific_name: coalesce(h.canonicalScientificName, h.latinName),
    synonyms: coalesce(h.localNames, []),
    simplisia_name: h.simplisiaName,
    score: score
} AS entity
ORDER BY score DESC
LIMIT $limit
"""

KNOWN_HERBS = {
    "jahe": "Zingiber officinale",
    "kunyit": "Curcuma longa",
    "temulawak": "Curcuma xanthorrhiza",
    "kencur": "Kaempferia galanga",
    "sambiloto": "Andrographis paniculata",
    "pegagan": "Centella asiatica",
    "meniran": "Phyllanthus niruri",
    "daun sirih": "Piper betle",
}


def resolve_entities(text: str) -> list[GraphEntity]:
    lower = text.lower()
    entities = []
    for local, scientific in KNOWN_HERBS.items():
        if re.search(rf"\b{re.escape(local)}\b", lower):
            entities.append(
                GraphEntity(
                    entity_type="plant", canonical_name=scientific, original_text=local, confidence=1.0
                )
            )
    compound_terms = ["kurkumin", "gingerol", "quercetin", "andrographolide", "asiaticoside"]
    for term in compound_terms:
        if term in lower:
            entities.append(
                GraphEntity(entity_type="compound", canonical_name=term, original_text=term, confidence=0.95)
            )
    if not entities:
        for token in re.findall(r"[A-Za-zÀ-ÿ]+", text)[:4]:
            if len(token) >= 4:
                entities.append(
                    GraphEntity(
                        entity_type="plant", canonical_name=token, original_text=token, confidence=0.45
                    )
                )
    return entities
