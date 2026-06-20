# Backend Enrichment Query Contract

## Recommendation query
`HERBAL_RECOMMENDATION_BY_SYMPTOMS` receives:

```json
{ "expanded_terms": ["batuk berdahak", "batuk", "ekspektoran"], "limit": 8 }
```

It matches `Symptom.name` plus `SymptomAlias.name`, returns `herb_id`, `local_name`, `scientific_name`, `safety_status`, `matched_symptoms`, `active_compounds`, `score`.

Fallback: `KnowledgeGraphRepository.recommend_herbs_legacy()` delegates to `plants_for_symptoms()` using old `USED_FOR`/`TherapeuticUse` path.

## Detail query
`HERB_ENRICHMENT_DETAIL` receives `herb_id`, `canonical_name`, `common_name`, returns section arrays for all v2 enrichment tabs. Mapper filters empty optional-match maps and dedupes nested sources.

## API response
`HerbalCandidate` now includes:
- `enrichment: HerbEnrichmentDetail`
- flat arrays: `traditional_uses`, `preparation_methods`, `usage_guidelines`, `safety_warnings`, `plant_parts`, `storage_guidelines`, `myth_facts`, `quality_standards`, `clinical_guidelines`, `drug_interactions_detail`, `contraindications_detail`, `pharmacokinetic_profiles`, `research_topics`, `claims`, `related_symptom_details`.

All output passes Pydantic + `json_safe`.
