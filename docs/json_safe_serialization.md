# JSON-safe Serialization

## Purpose
Neo4j temporal values (`neo4j.time.DateTime`, `Date`, `Time`, `Duration`) are not JSON serializable by Pydantic/FastAPI/Supabase JSONB by default.

## Utility
`app/core/json_safety.py::json_safe(value)` recursively converts:

- `neo4j.time.DateTime` → ISO string
- `neo4j.time.Date` → ISO string
- `neo4j.time.Time` → ISO string
- `neo4j.time.Duration` → string
- Python `datetime/date` → ISO string
- `Decimal` → float
- `Enum` → value
- Pydantic `BaseModel` → sanitized dict
- mappings/sequences → recursively sanitized structures
- fallback objects → string

## Usage
Use `model_dump(mode="python")` first, then `json_safe(...)`.

```python
payload = json_safe(candidate.model_dump(mode="python"))
```

Avoid `model_dump(mode="json")` when nested data may contain Neo4j driver objects.
