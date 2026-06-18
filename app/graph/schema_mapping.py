HERB_LABEL = "Herb"
COMPOUND_LABEL = "Compound"
THERAPEUTIC_USE_LABEL = "TherapeuticUse"
FAMILY_LABEL = "Family"
PROTEIN_TARGET_LABEL = "ProteinTarget"
TOXICITY_LABEL = "ToxicityCategory"
SOURCE_LABEL = "Source"

REL_HAS_COMPOUND = "HAS_COMPOUND"
REL_USED_FOR = "USED_FOR"
REL_BELONGS_TO = "BELONGS_TO"
REL_HAS_PROTEIN_TARGET = "HAS_PROTEIN_TARGET"
REL_HAS_TOXICITY = "HAS_TOXICITY"
REL_VERIFIED_BY = "VERIFIED_BY"
REL_HAS_COMPOUND_CLASS = "HAS_COMPOUND_CLASS"
REL_TARGETS_PROTEIN = "TARGETS_PROTEIN"


def canonical_herb_projection(alias: str = "h") -> str:
    return f"""
    {{
        plant_id: {alias}.id,
        local_name: {alias}.commonName,
        scientific_name: coalesce(
            {alias}.canonicalScientificName,
            {alias}.latinName
        ),
        latin_name: {alias}.latinName,
        synonyms: coalesce({alias}.localNames, []),
        simplisia_name: {alias}.simplisiaName,
        macroscopic_description: {alias}.macroscopicDesc,
        microscopic_description: {alias}.microscopicDesc,
        status: {alias}.status,
        species_number: {alias}.speciesNumber,
        last_updated: {alias}.lastUpdated
    }}
    """
