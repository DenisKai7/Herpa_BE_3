# Herbal Recommendation Timeout Fix Audit

## Cause
`POST /api/herbal-recommendations/analyze` was loading recommendation candidates and full enrichment detail in one request. `asyncio.gather()` called per-candidate detail queries. The large `HERB_ENRICHMENT_DETAIL` query chains many `OPTIONAL MATCH` clauses, creating row multiplication risk on Neo4j Aura → timeout/defunct connection.

## Backend touched
- `app/api/v1/recommendations.py`: add lazy detail endpoint.
- `app/logic/recommendation_orchestrator.py`: light analyze path, lazy detail skip, safe empty response.
- `app/graph/repositories.py`: light recommendation + core detail methods with timeout fallback.
- `app/graph/query_templates.py`: light queries + split `HERB_DETAIL_CORE`.
- `app/graph/neo4j_client.py`: per-query timeout and retry override.
- `app/core/config.py`: feature flags/timeouts.

## Frontend status
Full frontend app absent. Repo contains only `frontend_patch/`; patch adds detail API helper, detail response type, error parser.

## Non-target areas
Auth, chat, Supabase schema, MinIO, admin endpoints not changed.
