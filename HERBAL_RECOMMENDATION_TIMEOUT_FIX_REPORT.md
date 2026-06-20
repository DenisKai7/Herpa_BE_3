# Herbal Recommendation Timeout Fix Report

## Cause
Analyze endpoint memuat full enrichment detail per kandidat. Query detail besar + paralel ke Neo4j Aura → timeout/defunct connection.

## Backend changed
- `app/core/config.py`
- `app/graph/neo4j_client.py`
- `app/graph/query_templates.py`
- `app/graph/repositories.py`
- `app/logic/recommendation_orchestrator.py`
- `app/api/v1/recommendations.py`

## Frontend patch changed
- `frontend_patch/src/types/backend.ts`
- `frontend_patch/src/lib/backendApi.ts`
- `frontend_patch/src/lib/recommendationEnrichment.ts`

## Neo4j queries added
- `HERBAL_RECOMMENDATION_LIGHT_BY_SYMPTOMS`
- `HERBAL_RECOMMENDATION_LIGHT_LEGACY`
- `HERB_DETAIL_CORE`
- `database/neo4j/99_recommendation_performance_indexes.cypher`

## New endpoint
- `GET /api/herbal-recommendations/herbs/{herb_id}/detail`
- alias: `GET /api/v1/recommendations/herbs/{herb_id}/detail`

## Analyze compatibility
Existing `recommendations`, `options`, score/relevance/safety/symptom/compound fields remain. Enrichment fields remain but default empty in lazy mode.

## Lazy detail
Analyze returns light candidates only. Frontend calls detail endpoint when user opens Detail. Detail failure returns empty lists/fallback, not page failure.

## Timeout fallback
Recommendation repo catches Neo4j timeout, logs stage-specific error, tries legacy light query, then returns empty candidates with safe warning.

## Other features unchanged
Auth, chat, Supabase schema, MinIO, admin routes untouched.

## Validation
- `python -m compileall app`: passed.
- `ruff check .`: passed.
- `mypy app`: passed (`145 source files`).
- `pytest -q`: passed (`135 passed, 1 skipped, 1 warning`).
- Frontend `npm run lint` / `npm run build`: not run; no `package.json` or full frontend app in this backend repo.

## Remaining errors
- None in backend validation.
- Full frontend lazy-detail UI still must be applied in Herpa_FE repo; this repo only contains `frontend_patch/`.
