# Herbal Recommendation V3 Fix Audit

## Current issues
- Analyze path already stable but still slow because light query can scan via broad text matching.
- Backend score mapping can overstate primary symptom coverage.
- Detail endpoint exists but needs explicit lazy-detail log and frontend patch contract.
- Safety/evidence labels need sync: `limited` safety and `traditional` evidence are distinct states.

## Backend files
- `app/logic/recommendation_orchestrator.py`: analyze flow, score mapping, label helpers, metadata/logs.
- `app/graph/query_templates.py`: light queries, fallback queries, detail core query.
- `app/graph/repositories.py`: recommendation repository and timeout/fallback behavior.
- `app/api/v1/recommendations.py`: analyze + lazy detail endpoint.
- `app/services/recommendation/`: symptom alias/term expansion.

## Frontend files
- No full `frontend/` package in this backend repo.
- Patch files present: `frontend_patch/src/lib/backendApi.ts`, `frontend_patch/src/lib/recommendationEnrichment.ts`, `frontend_patch/src/types/backend.ts`.

## Scope
Only herbal recommendation backend + frontend patch docs/helpers. Auth, chat, Supabase, MinIO, admin unchanged.
