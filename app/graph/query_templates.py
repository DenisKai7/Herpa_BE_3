from app.graph.schema_mapping import canonical_herb_projection

HERB_FULLTEXT_SEARCH = f"""
CALL db.index.fulltext.queryNodes('herb_fulltext_idx', $search_term) YIELD node AS h, score
WHERE 'Herb' IN labels(h)
RETURN {canonical_herb_projection("h")} AS plant, score
ORDER BY score DESC
LIMIT $limit
"""

HERB_PROPERTY_SEARCH_FALLBACK = f"""
MATCH (h:Herb)
WHERE toLower(coalesce(h.commonName, '')) CONTAINS toLower($name)
   OR toLower(coalesce(h.canonicalScientificName, '')) CONTAINS toLower($name)
   OR toLower(coalesce(h.latinName, '')) CONTAINS toLower($name)
   OR any(localName IN coalesce(h.localNames, []) WHERE toLower(localName) CONTAINS toLower($name))
RETURN {canonical_herb_projection("h")} AS plant, 1.0 AS score
LIMIT $limit
"""

FIND_HERBS_FULLTEXT = HERB_FULLTEXT_SEARCH
FIND_HERBS_FALLBACK = HERB_PROPERTY_SEARCH_FALLBACK

HERB_BASIC_BY_ID = """
MATCH (h:Herb {id: $herb_id})
RETURN {
    id: h.id,
    plant_id: h.id,
    common_name: h.commonName,
    commonName: h.commonName,
    scientific_name: coalesce(h.canonicalScientificName, h.latinName),
    canonicalScientificName: h.canonicalScientificName,
    latinName: h.latinName,
    simplisia_name: h.simplisiaName,
    simplisiaName: h.simplisiaName,
    status: h.status
} AS herb
"""

HERB_COMPOUNDS = """
MATCH (h:Herb {id: $herb_id})-[:HAS_COMPOUND]->(c:Compound)
RETURN {
    name: c.name,
    pubchem_cid: c.pubchemCID,
    pubchemCID: c.pubchemCID,
    iupac: c.iupac,
    molecular_formula: c.molecularFormula,
    molecularFormula: c.molecularFormula,
    formula: c.molecularFormula,
    compound_class: c.compoundClass,
    compoundClass: c.compoundClass
} AS compound
LIMIT $limit
"""

HERB_THERAPEUTIC_USES = """
MATCH (h:Herb {id: $herb_id})-[:USED_FOR]->(u:TherapeuticUse)
RETURN {name: u.name, category: u.category} AS therapeutic_use
LIMIT $limit
"""

HERB_FAMILY = """
MATCH (h:Herb {id: $herb_id})-[:BELONGS_TO]->(family:Family)
RETURN {name: family.name, category: family.category} AS family
LIMIT $limit
"""

HERB_PROTEIN_TARGETS = """
MATCH (h:Herb {id: $herb_id})-[relationship:HAS_PROTEIN_TARGET]->(target:ProteinTarget)
RETURN {
    name: target.name,
    pdb_id: target.pdbID,
    category: target.category,
    mechanism: coalesce(relationship.mechanism, target.mechanism),
    affinity_range: coalesce(relationship.affinityRange, target.affinityRange)
} AS protein_target
LIMIT $limit
"""

HERB_TOXICITY = """
MATCH (h:Herb {id: $herb_id})-[:HAS_TOXICITY]->(toxicity:ToxicityCategory)
RETURN {name: toxicity.name, category: toxicity.category} AS toxicity
LIMIT $limit
"""

HERB_SOURCES = """
MATCH (h:Herb {id: $herb_id})-[:VERIFIED_BY]->(source:Source)
RETURN properties(source) AS source
LIMIT $limit
"""

HERBS_BY_THERAPEUTIC_USE = f"""
MATCH (h:Herb)-[:USED_FOR]->(use:TherapeuticUse)
WHERE toLower(coalesce(use.name, '')) CONTAINS toLower($term)
RETURN {canonical_herb_projection("h")} AS plant, 0.0 AS score
LIMIT $limit
"""

HERBS_BY_COMPOUND = f"""
MATCH (h:Herb)-[:HAS_COMPOUND]->(compound:Compound)
WHERE toLower(coalesce(compound.name, '')) CONTAINS toLower($compound_name)
RETURN {canonical_herb_projection("h")} AS plant, 0.0 AS score
LIMIT $limit
"""

COMPOUND_BY_NAME = """
MATCH (compound:Compound)
WHERE toLower(coalesce(compound.name, '')) CONTAINS toLower($name)
RETURN {
    name: compound.name,
    pubchem_cid: compound.pubchemCID,
    iupac: compound.iupac,
    molecular_formula: compound.molecularFormula,
    molar_mass: compound.molarMass,
    compound_class: compound.compoundClass
} AS compound
LIMIT $limit
"""

HERB_BY_NAME = FIND_HERBS_FALLBACK
PLANT_BY_NAME = HERB_BY_NAME
PLANTS_FOR_SYMPTOMS = HERBS_BY_THERAPEUTIC_USE
