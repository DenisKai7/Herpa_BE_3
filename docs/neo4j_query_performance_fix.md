# Neo4j Query Performance Fix

Changes:
- Per-query timeout in `Neo4jClient.read()`.
- Recommendation reads use `max_retries=0` and short timeout.
- Analyze uses light candidate query only.
- Detail uses `HERB_DETAIL_CORE` with `CALL (h)` subqueries, reducing cartesian row multiplication.
- Non-destructive indexes in `database/neo4j/99_recommendation_performance_indexes.cypher`.

No destructive Cypher. No seed rerun.
