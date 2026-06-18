# Recommendation Serialization Fix

## Problem
Recommendation candidates could contain raw Neo4j temporal values from source/evidence metadata. Persisting with `candidate.model_dump(mode="json")` raised:

```text
PydanticSerializationError: Unable to serialize unknown type: <class 'neo4j.time.DateTime'>
```

## Fix
- Neo4j client sanitizes every `record.data()` row using `json_safe()`.
- Recommendation persistence uses `json_safe(model_dump(mode="python"))`.
- Candidate/response dict fields sanitize nested values via validators.
- Source Cypher query avoids `properties(source)` and converts temporal fields with `toString()`.

## Supabase JSONB rule
All JSONB payloads must pass through `json_safe()` before insert/update.

## Safe pattern

```python
await self.db.insert(
    "recommendation_results",
    json_safe(
        {
            "result": candidate.model_dump(mode="python"),
        }
    ),
)
```

## Unsafe pattern

```python
candidate.model_dump(mode="json")
```
