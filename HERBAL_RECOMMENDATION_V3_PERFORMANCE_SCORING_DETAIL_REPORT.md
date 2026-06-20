# Herbal Recommendation V3 Performance, Scoring, Lazy Detail Report

## Cause
Analyze was slow because older light query could still use broad matching. Score was flat because backend treated one matched symptom as full relevance.

## Backend changed
- `app/services/recommendation/symptom_expander.py`
- `app/graph/query_templates.py`
- `app/graph/repositories.py`
- `app/logic/recommendation_orchestrator.py`
- `app/api/v1/recommendations.py`
- `app/models/recommendation.py`

## Frontend patch changed
- `frontend_patch/src/types/backend.ts`
- `frontend_patch/src/lib/recommendationEnrichment.ts`

## Cypher scripts added
- `database/neo4j/102_normalized_search_properties.cypher`
- `database/neo4j/103_recommendation_v3_indexes.cypher`

## Scoring V3
`score = primary*0.40 + expanded*0.20 + traditional*0.15 + compound*0.05 + safety*0.10 + primary_bonus`.

## Lazy detail
Detail endpoint logs `herbal_detail_stage detail_request_received` and returns core tabs.

## Validation
- `python -m compileall app`: passed.
- `ruff check .`: passed.
- `mypy app`: passed (`146 source files`).
- `pytest -q`: passed (`157 passed, 1 skipped, 1 warning`).
- Frontend `npm run lint` / `npm run build`: not run; no `package.json` in backend repo.

## Remaining errors
- Backend: none.
- Full frontend implementation still belongs in Herpa_FE; backend repo contains `frontend_patch/` only.
