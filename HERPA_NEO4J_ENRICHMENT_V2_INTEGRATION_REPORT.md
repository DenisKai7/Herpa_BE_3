# HERPA Neo4j Enrichment v2 Integration Report

## Backend files changed
- `app/models/common.py`
- `app/models/recommendation.py`
- `app/graph/query_templates.py`
- `app/graph/repositories.py`
- `app/logic/recommendation_orchestrator.py`
- `app/services/recommendation/enrichment_mapper.py`

## Frontend files changed
- `frontend_patch/src/types/backend.ts`
- `frontend_patch/src/lib/recommendationEnrichment.ts`

## Neo4j query added
- `HERBAL_RECOMMENDATION_BY_SYMPTOMS`: matches `Symptom` + `SymptomAlias` → herbs.
- `HERB_ENRICHMENT_DETAIL`: reads full enrichment sections for one herb.
- `database/neo4j/validate_enrichment_v2.cypher`: read-only schema validation.

## Pydantic models added
`TraditionalUseItem`, `PreparationMethodItem`, `UsageGuidelineItem`, `SafetyWarningItem`, `PlantPartItem`, `StorageGuidelineItem`, `MythFactItem`, `QualityStandardItem`, `ClinicalGuidelineItem`, `DrugInteractionItem`, `ContraindicationItem`, `PharmacokineticProfileItem`, `ResearchTopicItem`, `ClaimEvidenceItem`, `SymptomItem`, `HerbEnrichmentDetail`.

## TypeScript types added
`HerbalRecommendationItem`, `HerbEnrichmentDetail`, enrichment item types, and source helpers.

## Recommendation flow
1. Extract complaint terms.
2. Expand via `expand_symptoms()`.
3. Query `Symptom`/`SymptomAlias` using `recommend_herbs_by_symptoms()`.
4. If no results/error, fallback to legacy `plants_for_symptoms()`.
5. Fetch detail via `get_herb_enrichment_detail()` per candidate.
6. Attach `enrichment` + flat fields to `HerbalCandidate`.

## Example response: Kencur
```json
{
  "local_name": "Kencur",
  "scientific_name": "Kaempferia galanga",
  "enrichment": {
    "traditional_uses": [{ "title": "Batuk", "evidence_level": "traditional" }],
    "preparation_methods": [{ "title": "Seduhan", "steps": ["Cuci", "Seduh"] }],
    "usage_guidelines": [{ "dose_status": "not_clinically_established" }],
    "safety_warnings": [{ "severity": "caution" }]
  }
}
```

## Example response: Jahe
```json
{
  "local_name": "Jahe",
  "scientific_name": "Zingiber officinale",
  "enrichment": {
    "traditional_uses": [{ "title": "Mual ringan", "evidence_level": "traditional" }],
    "claims": [{ "claim_text": "Mendukung kenyamanan pencernaan", "evidence_level": "review" }]
  }
}
```

## Persona display difference
- `umum`: hides clinical dose; shows safe education sections.
- `peneliti`: shows claims, evidence, research topics, PK/quality where visible.
- `tenaga_medis`: shows clinical guidelines, interactions, contraindications, PK.

## Tests added
See `tests/unit/test_enrichment_v2.py`.

## Validation results
- `python -m compileall app`: passed.
- `ruff check .`: passed.
- `mypy app`: passed (`145 source files`).
- `pytest -q`: passed (`124 passed, 1 skipped, 1 warning`).
- Frontend `npm run lint` / `npm run build`: not run because this backend repo has no `package.json` or full frontend app; only `frontend_patch/` exists.

## Remaining errors
- None in backend validation.
- Frontend UI tab implementation must be applied in the separate Herpa_FE repo; this repo only contains patch types/helpers.
