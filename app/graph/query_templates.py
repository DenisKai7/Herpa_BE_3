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
RETURN {
    type: 'neo4j',
    source_id: coalesce(source.id, source.identifier, source.name),
    id: source.id,
    title: source.name,
    name: source.name,
    identifier: source.identifier,
    year: source.year,
    url: source.url,
    evidence_level: source.evidenceLevel,
    updated_at: toString(source.updatedAt),
    created_at: toString(source.createdAt),
    last_updated: toString(source.lastUpdated)
} AS source
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

HERB_ENRICHMENT_DETAIL = """
MATCH (h:Herb)
WHERE h.id = $herb_id
   OR toLower(coalesce(h.canonicalScientificName, '')) = toLower($canonical_name)
   OR toLower(coalesce(h.latinName, '')) = toLower($canonical_name)
   OR toLower(coalesce(h.commonName, '')) = toLower($common_name)
OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse)
OPTIONAL MATCH (tu)-[:VERIFIED_BY]->(tuSource:Source)
OPTIONAL MATCH (h)-[:HAS_PREPARATION]->(prep:PreparationMethod)
OPTIONAL MATCH (prep)-[:USES_FORMULATION]->(formulation:Formulation)
OPTIONAL MATCH (prep)-[:VERIFIED_BY]->(prepSource:Source)
OPTIONAL MATCH (h)-[:HAS_USAGE_GUIDELINE]->(guide:UsageGuideline)
OPTIONAL MATCH (guide)-[:VERIFIED_BY]->(guideSource:Source)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(warning:SafetyWarning)
OPTIONAL MATCH (warning)-[:APPLIES_TO_RISK]->(warningRisk:PopulationRisk)
OPTIONAL MATCH (warning)-[:VERIFIED_BY]->(warningSource:Source)
OPTIONAL MATCH (h)-[:USES_PART]->(part:PlantPart)
OPTIONAL MATCH (h)-[:HAS_STORAGE_GUIDELINE]->(storage:StorageGuideline)
OPTIONAL MATCH (h)-[:HAS_MYTH_FACT]->(myth:MythFact)
OPTIONAL MATCH (h)-[:HAS_QUALITY_STANDARD]->(quality:QualityStandard)
OPTIONAL MATCH (h)-[:HAS_CLINICAL_GUIDELINE]->(clinical:ClinicalGuideline)
OPTIONAL MATCH (clinical)-[:VISIBLE_TO]->(clinicalAudience:Audience)
OPTIONAL MATCH (clinical)-[:VERIFIED_BY]->(clinicalSource:Source)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(interaction:DrugInteraction)
OPTIONAL MATCH (interaction)-[:APPLIES_TO_RISK]->(interactionRisk:PopulationRisk)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
OPTIONAL MATCH (contra)-[:APPLIES_TO_RISK]->(contraRisk:PopulationRisk)
OPTIONAL MATCH (h)-[:HAS_PHARMACOKINETIC_PROFILE]->(pk:PharmacokineticProfile)
OPTIONAL MATCH (h)-[:HAS_RESEARCH_TOPIC]->(research:ResearchTopic)
OPTIONAL MATCH (research)-[:VISIBLE_TO]->(researchAudience:Audience)
OPTIONAL MATCH (h)-[:HAS_CLAIM]->(claim:Claim)
OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
OPTIONAL MATCH (evidence)-[:FROM_SOURCE]->(evidenceSource:Source)
OPTIONAL MATCH (h)-[:MAY_HELP_WITH]->(symptom:Symptom)
OPTIONAL MATCH (symptom)-[:HAS_ALIAS]->(alias:SymptomAlias)
RETURN h.id AS herb_id,
  collect(DISTINCT {id: tu.id, title: tu.title, description: tu.description, category: tu.category, evidence_level: coalesce(tu.evidence_level, 'traditional'), verification_status: coalesce(tu.verification_status, 'limited'), recommendation_weight: tu.recommendation_weight, sources: CASE WHEN tuSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(tuSource.id, tuSource.identifier, tuSource.name), title: tuSource.name, identifier: tuSource.identifier, year: tuSource.year, url: tuSource.url}] END}) AS traditional_uses,
  collect(DISTINCT {id: prep.id, title: prep.title, method_type: prep.method_type, plant_part: prep.plant_part, ingredients: coalesce(prep.ingredients, []), steps: coalesce(prep.steps, []), notes: prep.notes, verification_status: coalesce(prep.verification_status, 'limited'), formulations: CASE WHEN formulation IS NULL THEN [] ELSE [formulation.name] END, sources: CASE WHEN prepSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(prepSource.id, prepSource.identifier, prepSource.name), title: prepSource.name, identifier: prepSource.identifier, year: prepSource.year, url: prepSource.url}] END}) AS preparation_methods,
  collect(DISTINCT {id: guide.id, title: guide.title, description: guide.description, frequency_text: guide.frequency_text, duration_text: guide.duration_text, dose_status: coalesce(guide.dose_status, 'not_clinically_established'), verification_status: coalesce(guide.verification_status, 'limited'), sources: CASE WHEN guideSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(guideSource.id, guideSource.identifier, guideSource.name), title: guideSource.name, identifier: guideSource.identifier, year: guideSource.year, url: guideSource.url}] END}) AS usage_guidelines,
  collect(DISTINCT {id: warning.id, title: warning.title, description: warning.description, severity: coalesce(warning.severity, 'caution'), verification_status: coalesce(warning.verification_status, 'limited'), population_risks: CASE WHEN warningRisk IS NULL THEN [] ELSE [coalesce(warningRisk.name, warningRisk.id)] END, sources: CASE WHEN warningSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(warningSource.id, warningSource.identifier, warningSource.name), title: warningSource.name, identifier: warningSource.identifier, year: warningSource.year, url: warningSource.url}] END}) AS safety_warnings,
  collect(DISTINCT {id: part.id, name: part.name, description: part.description}) AS plant_parts,
  collect(DISTINCT {id: storage.id, title: storage.title, description: storage.description, storage_temperature: storage.storage_temperature, notes: storage.notes, verification_status: coalesce(storage.verification_status, 'limited')}) AS storage_guidelines,
  collect(DISTINCT {id: myth.id, claim: myth.claim, fact: myth.fact, risk_level: myth.risk_level, verification_status: coalesce(myth.verification_status, 'limited')}) AS myth_facts,
  collect(DISTINCT {id: quality.id, parameter: quality.parameter, value: quality.value, source_standard: quality.source_standard, verification_status: coalesce(quality.verification_status, 'limited')}) AS quality_standards,
  collect(DISTINCT {id: clinical.id, mechanism: clinical.mechanism, therapeutic_dose_text: clinical.therapeutic_dose_text, notes: clinical.notes, visible_to: CASE WHEN clinicalAudience IS NULL THEN [] ELSE [clinicalAudience.id] END, sources: CASE WHEN clinicalSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(clinicalSource.id, clinicalSource.identifier, clinicalSource.name), title: clinicalSource.name, identifier: clinicalSource.identifier, year: clinicalSource.year, url: clinicalSource.url}] END}) AS clinical_guidelines,
  collect(DISTINCT {id: interaction.id, substance: interaction.substance, description: interaction.description, severity: coalesce(interaction.severity, 'caution'), population_risks: CASE WHEN interactionRisk IS NULL THEN [] ELSE [coalesce(interactionRisk.name, interactionRisk.id)] END}) AS drug_interactions,
  collect(DISTINCT {id: contra.id, condition: contra.condition, description: contra.description, severity: coalesce(contra.severity, 'caution'), population_risks: CASE WHEN contraRisk IS NULL THEN [] ELSE [coalesce(contraRisk.name, contraRisk.id)] END}) AS contraindications,
  collect(DISTINCT {absorption: pk.absorption, distribution: pk.distribution, metabolism: pk.metabolism, excretion: pk.excretion}) AS pharmacokinetic_profiles,
  collect(DISTINCT {id: research.id, title: research.title, category: research.category, visible_to: CASE WHEN researchAudience IS NULL THEN [] ELSE [researchAudience.id] END}) AS research_topics,
  collect(DISTINCT {claim_id: claim.id, claim_text: claim.text, claim_type: claim.claim_type, evidence_level: coalesce(evidence.evidence_level, claim.evidence_level, 'unknown'), evidence_summary: evidence.summary, sources: CASE WHEN evidenceSource IS NULL THEN [] ELSE [{type: 'neo4j', source_id: coalesce(evidenceSource.id, evidenceSource.identifier, evidenceSource.name), title: evidenceSource.name, identifier: evidenceSource.identifier, year: evidenceSource.year, url: evidenceSource.url}] END}) AS claims,
  collect(DISTINCT {id: symptom.id, name: symptom.name, category: symptom.category, aliases: CASE WHEN alias IS NULL THEN [] ELSE [alias.name] END}) AS related_symptoms
LIMIT 1
"""

HERBAL_RECOMMENDATION_BY_SYMPTOMS = """
MATCH (s:Symptom)
WHERE any(term IN $expanded_terms WHERE toLower(s.name) CONTAINS toLower(term))
   OR EXISTS {
      MATCH (s)-[:HAS_ALIAS]->(a:SymptomAlias)
      WHERE any(term IN $expanded_terms WHERE toLower(a.name) CONTAINS toLower(term))
   }
MATCH (h:Herb)-[:MAY_HELP_WITH]->(s)
OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse)
OPTIONAL MATCH (h)-[:HAS_CLAIM]->(claim:Claim)
OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(warning:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(interaction:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
OPTIONAL MATCH (h)-[:HAS_COMPOUND]->(compound:Compound)
WITH h,
  collect(DISTINCT s.name) AS matched_symptoms,
  collect(DISTINCT tu.evidence_level) AS evidence_levels,
  collect(DISTINCT claim.id) AS claims,
  collect(DISTINCT evidence.id) AS evidences,
  collect(DISTINCT warning.id) AS warnings,
  collect(DISTINCT interaction.id) AS interactions,
  collect(DISTINCT contra.id) AS contraindications,
  collect(DISTINCT compound.name) AS compounds
WITH h, matched_symptoms, compounds,
  size(matched_symptoms) AS symptom_match_count,
  CASE WHEN 'clinical' IN evidence_levels THEN 1.0 WHEN 'pharmacopoeia' IN evidence_levels THEN 0.85 WHEN 'review' IN evidence_levels THEN 0.75 WHEN 'preclinical' IN evidence_levels THEN 0.6 WHEN 'traditional' IN evidence_levels THEN 0.45 ELSE 0.3 END AS evidence_score,
  CASE WHEN size(contraindications) > 0 THEN 0.25 WHEN size(interactions) > 0 THEN 0.45 WHEN size(warnings) > 0 THEN 0.6 ELSE 0.75 END AS safety_score
WITH h, matched_symptoms, compounds, evidence_score, safety_score,
  ((toFloat(symptom_match_count) * 0.40) + (evidence_score * 0.25) + (safety_score * 0.20) + (CASE WHEN size(compounds) > 0 THEN 0.15 ELSE 0.0 END)) AS raw_score
RETURN h.id AS herb_id,
  h.commonName AS local_name,
  coalesce(h.canonicalScientificName, h.latinName) AS scientific_name,
  h.safety_status AS safety_status,
  matched_symptoms,
  compounds[0..10] AS active_compounds,
  raw_score AS score
ORDER BY score DESC
LIMIT $limit
"""

HERBAL_RECOMMENDATION_LIGHT_BY_SYMPTOMS = """
MATCH (s:Symptom)
WHERE any(term IN $terms WHERE toLower(s.name) = toLower(term))
   OR any(term IN $terms WHERE toLower(s.name) CONTAINS toLower(term))
   OR EXISTS {
      MATCH (s)-[:HAS_ALIAS]->(a:SymptomAlias)
      WHERE any(term IN $terms WHERE toLower(a.name) = toLower(term))
         OR any(term IN $terms WHERE toLower(a.name) CONTAINS toLower(term))
   }
MATCH (h:Herb)-[:MAY_HELP_WITH]->(s)
OPTIONAL MATCH (s)-[:HAS_ALIAS]->(alias:SymptomAlias)
OPTIONAL MATCH (h)-[:HAS_COMPOUND]->(c:Compound)
OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(w:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(i:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
OPTIONAL MATCH (h)-[:HAS_TOXICITY]->(tox:ToxicityCategory)
WITH h, s,
  collect(DISTINCT alias.name) AS symptom_aliases,
  collect(DISTINCT c.name)[0..8] AS active_compounds,
  collect(DISTINCT tu.title)[0..5] AS traditional_uses,
  count(DISTINCT w) AS warning_count,
  count(DISTINCT i) AS interaction_count,
  count(DISTINCT contra) AS contraindication_count,
  count(DISTINCT tox) AS toxicity_count,
  CASE
    WHEN any(term IN $terms WHERE toLower(s.name) = toLower(term)) THEN 1.0
    WHEN any(term IN $terms WHERE toLower(s.name) CONTAINS toLower(term)) THEN 0.75
    WHEN any(aliasName IN collect(DISTINCT alias.name) WHERE any(term IN $terms WHERE toLower(aliasName) = toLower(term))) THEN 0.85
    WHEN any(aliasName IN collect(DISTINCT alias.name) WHERE any(term IN $terms WHERE toLower(aliasName) CONTAINS toLower(term))) THEN 0.65
    ELSE 0.35
  END AS symptom_match_quality
WITH h,
  collect(DISTINCT s.name)[0..5] AS matched_symptoms,
  active_compounds,
  traditional_uses,
  max(symptom_match_quality) AS best_symptom_match_score,
  avg(symptom_match_quality) AS avg_symptom_match_score,
  warning_count,
  interaction_count,
  contraindication_count,
  toxicity_count
WITH h, matched_symptoms, active_compounds, traditional_uses, best_symptom_match_score, avg_symptom_match_score,
  CASE WHEN size(active_compounds) > 0 THEN 1.0 ELSE 0.0 END AS compound_score,
  CASE WHEN size(traditional_uses) > 0 THEN 1.0 ELSE 0.0 END AS traditional_use_score,
  CASE
    WHEN contraindication_count > 0 THEN 0.30
    WHEN interaction_count > 0 THEN 0.45
    WHEN warning_count > 0 THEN 0.60
    WHEN toxicity_count > 0 THEN 0.60
    ELSE 0.70
  END AS safety_score,
  CASE
    WHEN contraindication_count > 0 THEN 'caution'
    WHEN interaction_count > 0 THEN 'caution'
    WHEN warning_count > 0 THEN 'caution'
    WHEN toxicity_count > 0 THEN 'caution'
    ELSE coalesce(h.safety_status, 'unknown')
  END AS safety_status
WITH h, matched_symptoms, active_compounds, traditional_uses, safety_status, best_symptom_match_score, avg_symptom_match_score, compound_score, traditional_use_score, safety_score,
  (best_symptom_match_score * 0.45 + avg_symptom_match_score * 0.15 + traditional_use_score * 0.15 + compound_score * 0.10 + safety_score * 0.15) AS score
RETURN h.id AS herb_id,
  h.commonName AS local_name,
  coalesce(h.canonicalScientificName, h.latinName) AS scientific_name,
  matched_symptoms,
  active_compounds,
  traditional_uses,
  safety_status,
  best_symptom_match_score AS symptom_match_score,
  avg_symptom_match_score AS average_symptom_match_score,
  compound_score,
  traditional_use_score,
  safety_score,
  score
ORDER BY score DESC
LIMIT $limit
"""

HERBAL_RECOMMENDATION_LIGHT_LEGACY = """
MATCH (h:Herb)-[:USED_FOR]->(u:TherapeuticUse)
WHERE any(term IN $terms WHERE toLower(u.name) = toLower(term))
   OR any(term IN $terms WHERE toLower(u.name) CONTAINS toLower(term))
OPTIONAL MATCH (h)-[:HAS_COMPOUND]->(c:Compound)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(w:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(i:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
WITH h,
  collect(DISTINCT u.name)[0..5] AS matched_symptoms,
  collect(DISTINCT c.name)[0..8] AS active_compounds,
  count(DISTINCT w) AS warning_count,
  count(DISTINCT i) AS interaction_count,
  count(DISTINCT contra) AS contraindication_count,
  CASE
    WHEN any(term IN $terms WHERE any(useName IN collect(DISTINCT u.name) WHERE toLower(useName) = toLower(term))) THEN 1.0
    ELSE 0.55
  END AS symptom_match_score
WITH h, matched_symptoms, active_compounds, symptom_match_score,
  CASE WHEN size(active_compounds) > 0 THEN 1.0 ELSE 0.0 END AS compound_score,
  CASE
    WHEN contraindication_count > 0 THEN 0.30
    WHEN interaction_count > 0 THEN 0.45
    WHEN warning_count > 0 THEN 0.60
    ELSE 0.70
  END AS safety_score,
  CASE
    WHEN contraindication_count > 0 THEN 'caution'
    WHEN interaction_count > 0 THEN 'caution'
    WHEN warning_count > 0 THEN 'caution'
    ELSE coalesce(h.safety_status, 'unknown')
  END AS safety_status
WITH h, matched_symptoms, active_compounds, symptom_match_score, compound_score, safety_score, safety_status,
  (symptom_match_score * 0.65 + compound_score * 0.15 + safety_score * 0.20) AS score
RETURN h.id AS herb_id,
  h.commonName AS local_name,
  coalesce(h.canonicalScientificName, h.latinName) AS scientific_name,
  matched_symptoms,
  active_compounds,
  safety_status,
  symptom_match_score,
  compound_score,
  safety_score,
  score
ORDER BY score DESC
LIMIT $limit
"""

HERB_DETAIL_CORE = """
MATCH (h:Herb {id: $herb_id})
CALL (h) { OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse) RETURN collect(DISTINCT {id: tu.id, title: tu.title, description: tu.description, category: tu.category, evidence_level: coalesce(tu.evidence_level, 'traditional'), verification_status: coalesce(tu.verification_status, 'limited')}) AS traditional_uses }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_PREPARATION]->(prep:PreparationMethod) OPTIONAL MATCH (prep)-[:USES_FORMULATION]->(form:Formulation) RETURN collect(DISTINCT {id: prep.id, title: prep.title, method_type: prep.method_type, plant_part: prep.plant_part, ingredients: coalesce(prep.ingredients, []), steps: coalesce(prep.steps, []), notes: prep.notes, verification_status: coalesce(prep.verification_status, 'limited'), formulations: CASE WHEN form IS NULL THEN [] ELSE [form.name] END}) AS preparation_methods }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_USAGE_GUIDELINE]->(guide:UsageGuideline) RETURN collect(DISTINCT {id: guide.id, title: guide.title, description: guide.description, frequency_text: guide.frequency_text, duration_text: guide.duration_text, dose_status: coalesce(guide.dose_status, 'not_clinically_established'), verification_status: coalesce(guide.verification_status, 'limited')}) AS usage_guidelines }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_WARNING]->(warn:SafetyWarning) OPTIONAL MATCH (warn)-[:APPLIES_TO_RISK]->(risk:PopulationRisk) RETURN collect(DISTINCT {id: warn.id, title: warn.title, description: warn.description, severity: coalesce(warn.severity, 'caution'), verification_status: coalesce(warn.verification_status, 'limited'), population_risks: CASE WHEN risk IS NULL THEN [] ELSE [coalesce(risk.name, risk.id)] END}) AS safety_warnings }
CALL (h) { OPTIONAL MATCH (h)-[:USES_PART]->(part:PlantPart) RETURN collect(DISTINCT {id: part.id, name: part.name, description: part.description}) AS plant_parts }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_STORAGE_GUIDELINE]->(storage:StorageGuideline) RETURN collect(DISTINCT {id: storage.id, title: storage.title, description: storage.description, storage_temperature: storage.storage_temperature, notes: storage.notes, verification_status: coalesce(storage.verification_status, 'limited')}) AS storage_guidelines }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_MYTH_FACT]->(myth:MythFact) RETURN collect(DISTINCT {id: myth.id, claim: myth.claim, fact: myth.fact, risk_level: myth.risk_level, verification_status: coalesce(myth.verification_status, 'limited')}) AS myth_facts }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_QUALITY_STANDARD]->(quality:QualityStandard) RETURN collect(DISTINCT {id: quality.id, parameter: quality.parameter, value: quality.value, source_standard: quality.source_standard, verification_status: coalesce(quality.verification_status, 'limited')}) AS quality_standards }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_CLINICAL_GUIDELINE]->(clinical:ClinicalGuideline) OPTIONAL MATCH (clinical)-[:VISIBLE_TO]->(aud:Audience) RETURN collect(DISTINCT {id: clinical.id, mechanism: clinical.mechanism, therapeutic_dose_text: clinical.therapeutic_dose_text, notes: clinical.notes, visible_to: CASE WHEN aud IS NULL THEN [] ELSE [aud.id] END}) AS clinical_guidelines }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(interaction:DrugInteraction) OPTIONAL MATCH (interaction)-[:APPLIES_TO_RISK]->(risk:PopulationRisk) RETURN collect(DISTINCT {id: interaction.id, substance: interaction.substance, description: interaction.description, severity: coalesce(interaction.severity, 'caution'), population_risks: CASE WHEN risk IS NULL THEN [] ELSE [coalesce(risk.name, risk.id)] END}) AS drug_interactions }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication) OPTIONAL MATCH (contra)-[:APPLIES_TO_RISK]->(risk:PopulationRisk) RETURN collect(DISTINCT {id: contra.id, condition: contra.condition, description: contra.description, severity: coalesce(contra.severity, 'caution'), population_risks: CASE WHEN risk IS NULL THEN [] ELSE [coalesce(risk.name, risk.id)] END}) AS contraindications }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_PHARMACOKINETIC_PROFILE]->(pk:PharmacokineticProfile) RETURN collect(DISTINCT {absorption: pk.absorption, distribution: pk.distribution, metabolism: pk.metabolism, excretion: pk.excretion}) AS pharmacokinetic_profiles }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_RESEARCH_TOPIC]->(research:ResearchTopic) OPTIONAL MATCH (research)-[:VISIBLE_TO]->(aud:Audience) RETURN collect(DISTINCT {id: research.id, title: research.title, category: research.category, visible_to: CASE WHEN aud IS NULL THEN [] ELSE [aud.id] END}) AS research_topics }
CALL (h) { OPTIONAL MATCH (h)-[:HAS_CLAIM]->(claim:Claim) OPTIONAL MATCH (claim)-[:SUPPORTED_BY]->(evidence:Evidence) RETURN collect(DISTINCT {claim_id: claim.id, claim_text: claim.text, claim_type: claim.claim_type, evidence_level: coalesce(evidence.evidence_level, claim.evidence_level, 'unknown'), evidence_summary: evidence.summary}) AS claims }
CALL (h) { OPTIONAL MATCH (h)-[:MAY_HELP_WITH]->(symptom:Symptom) OPTIONAL MATCH (symptom)-[:HAS_ALIAS]->(alias:SymptomAlias) RETURN collect(DISTINCT {id: symptom.id, name: symptom.name, category: symptom.category, aliases: CASE WHEN alias IS NULL THEN [] ELSE [alias.name] END}) AS related_symptoms }
RETURN h.id AS herb_id, h.commonName AS common_name, coalesce(h.canonicalScientificName, h.latinName) AS scientific_name, traditional_uses, preparation_methods, usage_guidelines, safety_warnings, plant_parts, storage_guidelines, myth_facts, quality_standards, clinical_guidelines, drug_interactions, contraindications, pharmacokinetic_profiles, research_topics, claims, related_symptoms
LIMIT 1
"""

HERBAL_RECOMMENDATION_LIGHT_V3 = """
MATCH (h:Herb)-[:MAY_HELP_WITH]->(s:Symptom)
WHERE s.name_lc IN $expanded_terms
OPTIONAL MATCH (s)-[:HAS_ALIAS]->(a:SymptomAlias)
OPTIONAL MATCH (h)-[:HAS_COMPOUND]->(c:Compound)
OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(w:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(i:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
OPTIONAL MATCH (h)-[:HAS_TOXICITY]->(tox:ToxicityCategory)
WITH h,
  collect(DISTINCT s.name_lc) AS matched_symptom_lc,
  collect(DISTINCT s.name)[0..6] AS matched_symptoms,
  collect(DISTINCT a.name_lc) AS alias_lc,
  collect(DISTINCT c.name)[0..8] AS active_compounds,
  collect(DISTINCT tu.title)[0..5] AS traditional_uses,
  count(DISTINCT w) AS warning_count,
  count(DISTINCT i) AS interaction_count,
  count(DISTINCT contra) AS contraindication_count,
  count(DISTINCT tox) AS toxicity_count
WITH h, matched_symptom_lc, matched_symptoms, alias_lc, active_compounds, traditional_uses, warning_count, interaction_count, contraindication_count, toxicity_count,
  size([term IN $primary_terms WHERE term IN matched_symptom_lc]) AS primary_direct_hits,
  size([term IN $expanded_terms WHERE term IN matched_symptom_lc]) AS expanded_direct_hits,
  size($primary_terms) AS primary_count,
  size($expanded_terms) AS expanded_count
WITH h, matched_symptoms, active_compounds, traditional_uses, warning_count, interaction_count, contraindication_count, toxicity_count,
  CASE WHEN primary_count = 0 THEN 0.0 ELSE toFloat(primary_direct_hits) / toFloat(primary_count) END AS primary_coverage_score,
  CASE WHEN expanded_count = 0 THEN 0.0 ELSE toFloat(expanded_direct_hits) / toFloat(expanded_count) END AS expanded_coverage_score,
  CASE WHEN size(traditional_uses) > 0 THEN 1.0 ELSE 0.0 END AS traditional_use_score,
  CASE WHEN size(active_compounds) > 0 THEN 1.0 ELSE 0.0 END AS compound_score,
  CASE WHEN contraindication_count > 0 THEN 0.35 WHEN interaction_count > 0 THEN 0.50 WHEN warning_count > 0 THEN 0.65 WHEN toxicity_count > 0 THEN 0.65 ELSE 0.75 END AS safety_score,
  CASE WHEN contraindication_count > 0 THEN 'caution' WHEN interaction_count > 0 THEN 'caution' WHEN warning_count > 0 THEN 'limited' WHEN toxicity_count > 0 THEN 'limited' ELSE coalesce(h.safety_status, 'unknown') END AS safety_status
WITH h, matched_symptoms, active_compounds, traditional_uses, safety_status, primary_coverage_score, expanded_coverage_score, traditional_use_score, compound_score, safety_score,
  (primary_coverage_score * 0.40 + expanded_coverage_score * 0.20 + traditional_use_score * 0.15 + compound_score * 0.05 + safety_score * 0.10 + CASE WHEN primary_coverage_score >= 1.0 THEN 0.10 WHEN primary_coverage_score >= 0.5 THEN 0.05 ELSE 0.0 END) AS score
RETURN h.id AS herb_id,
  h.commonName AS local_name,
  coalesce(h.canonicalScientificName, h.latinName) AS scientific_name,
  matched_symptoms,
  active_compounds,
  traditional_uses,
  safety_status,
  primary_coverage_score,
  expanded_coverage_score,
  traditional_use_score,
  compound_score,
  safety_score,
  score
ORDER BY score DESC
LIMIT $limit
"""

HERBAL_RECOMMENDATION_FULLTEXT_FALLBACK = """
CALL db.index.fulltext.queryNodes('symptom_alias_fulltext_idx', $fulltext_query)
YIELD node, score AS text_score
WITH collect(DISTINCT toLower(node.name))[0..20] AS found_terms
MATCH (h:Herb)-[:MAY_HELP_WITH]->(s:Symptom)
WHERE toLower(s.name) IN found_terms
OPTIONAL MATCH (h)-[:HAS_COMPOUND]->(c:Compound)
OPTIONAL MATCH (h)-[:HAS_TRADITIONAL_USE]->(tu:TraditionalUse)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(w:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(i:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
WITH h,
  collect(DISTINCT s.name)[0..6] AS matched_symptoms,
  collect(DISTINCT c.name)[0..8] AS active_compounds,
  collect(DISTINCT tu.title)[0..5] AS traditional_uses,
  count(DISTINCT w) AS warning_count,
  count(DISTINCT i) AS interaction_count,
  count(DISTINCT contra) AS contraindication_count
WITH h, matched_symptoms, active_compounds, traditional_uses,
  CASE WHEN size(traditional_uses) > 0 THEN 0.7 ELSE 0.4 END AS symptom_score,
  CASE WHEN size(active_compounds) > 0 THEN 1.0 ELSE 0.0 END AS compound_score,
  CASE WHEN contraindication_count > 0 THEN 0.35 WHEN interaction_count > 0 THEN 0.50 WHEN warning_count > 0 THEN 0.65 ELSE 0.75 END AS safety_score,
  CASE WHEN contraindication_count > 0 THEN 'caution' WHEN interaction_count > 0 THEN 'caution' WHEN warning_count > 0 THEN 'limited' ELSE coalesce(h.safety_status, 'unknown') END AS safety_status
WITH h, matched_symptoms, active_compounds, traditional_uses, safety_status, symptom_score, compound_score, safety_score,
  (symptom_score * 0.65 + compound_score * 0.10 + safety_score * 0.15) AS score
RETURN h.id AS herb_id,
  h.commonName AS local_name,
  coalesce(h.canonicalScientificName, h.latinName) AS scientific_name,
  matched_symptoms,
  active_compounds,
  traditional_uses,
  safety_status,
  symptom_score AS primary_coverage_score,
  0.0 AS expanded_coverage_score,
  CASE WHEN size(traditional_uses) > 0 THEN 1.0 ELSE 0.0 END AS traditional_use_score,
  compound_score,
  safety_score,
  score
ORDER BY score DESC
LIMIT $limit
"""
