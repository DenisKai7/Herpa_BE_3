# Neo4j Datetime Serialization Audit

## Error
`PydanticSerializationError: Unable to serialize unknown type: <class 'neo4j.time.DateTime'>` occurred during recommendation persistence.

## Failing location
`app/logic/recommendation_orchestrator.py` persisted recommendation results with:

```python
candidate.model_dump(mode="json")
```

This fails when nested candidate fields include raw Neo4j temporal objects.

## Likely carrier fields
Neo4j source/herb metadata can include temporal properties such as:

- `updatedAt`
- `lastUpdated`
- `createdAt`

These may enter recommendation candidates through raw source/evidence dictionaries, especially from `VERIFIED_BY` source data.

## Files audited
- `app/logic/recommendation_orchestrator.py`
- `app/graph/neo4j_client.py`
- `app/graph/repositories.py`
- `app/graph/query_templates.py`
- `app/models/recommendation.py`
- `app/core/logging.py`
- `app/api/v1/recommendations.py`
- `tests/`

## Risky patterns found
- `candidate.model_dump(mode="json")` for Supabase JSONB result payload.
- `response.model_dump(mode="json")` for mock history.
- `properties(source)` in Cypher source query, which can return raw temporal fields.
- Neo4j client returned `record.data()` without recursive sanitization.

## Fix summary
- Added recursive `json_safe()` utility.
- Neo4j client now sanitizes every query row.
- Recommendation orchestrator persists `json_safe(model_dump(mode="python"))`.
- Response/candidate dict fields sanitize nested values.
- Source Cypher query now returns explicit fields with temporal values converted through `toString()`.
