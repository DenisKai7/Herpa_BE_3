# NEO4J DATETIME SERIALIZATION FIX REPORT

## 1. Penyebab error serialization
Recommendation candidate membawa nested raw Neo4j temporal object (`neo4j.time.DateTime`) dari hasil query/source metadata. Saat persistence ke Supabase, kode memakai `candidate.model_dump(mode="json")`, sehingga Pydantic gagal serialize tipe Neo4j driver.

## 2. Field pembawa `neo4j.time.DateTime`
Kemungkinan utama:

- `source.updatedAt`
- `source.createdAt`
- `source.lastUpdated`
- nested `evidence_sources` / source dictionaries dari relasi `VERIFIED_BY`

Audit menemukan `properties(source)` di `app/graph/query_templates.py`, yang dapat membawa semua property mentah termasuk temporal Neo4j.

## 3. Backend files changed
- `app/core/json_safety.py`
- `app/graph/neo4j_client.py`
- `app/graph/query_templates.py`
- `app/logic/recommendation_orchestrator.py`
- `app/models/recommendation.py`
- `tests/contract/test_json_safety.py`
- `docs/neo4j_datetime_serialization_audit.md`
- `docs/json_safe_serialization.md`
- `docs/recommendation_serialization_fix.md`

## 4. New files created
- `app/core/json_safety.py`
- `tests/contract/test_json_safety.py`
- `docs/neo4j_datetime_serialization_audit.md`
- `docs/json_safe_serialization.md`
- `docs/recommendation_serialization_fix.md`

## 5. JSON sanitization strategy
`json_safe()` recursively converts:

- Neo4j `DateTime`, `Date`, `Time` → ISO string
- Neo4j `Duration` → string
- Python `datetime/date` → ISO string
- `Decimal` → float
- `Enum` → value
- Pydantic model → `model_dump(mode="python")` then sanitize
- dict/list/tuple/nested objects → recursive JSON-safe structure
- unknown object → string fallback

## 6. Recommendation orchestrator changes
Replaced unsafe persistence:

```python
candidate.model_dump(mode="json")
```

with:

```python
json_safe(candidate.model_dump(mode="python"))
```

Also sanitized:

- mock history input/response
- `recommendation_sessions.input`
- `recommendation_results.result`
- full Supabase insert payloads

## 7. Neo4j client/repository changes
`app/graph/neo4j_client.py` now returns:

```python
json_safe(record.data())
```

so all query rows are sanitized before repository/orchestrator receives them.

`app/graph/query_templates.py` no longer uses `properties(source)` for herb sources. It now returns explicit source fields and converts temporal fields with `toString()`.

## 8. Tests added
- `test_json_safe_converts_neo4j_datetime`
- `test_json_safe_converts_neo4j_date`
- `test_json_safe_converts_neo4j_time`
- `test_json_safe_converts_neo4j_duration`
- `test_json_safe_converts_nested_neo4j_datetime`
- `test_json_safe_converts_pydantic_model`
- `test_recommendation_candidate_with_neo4j_datetime_serializes`
- `test_recommendation_result_payload_is_json_safe`
- `test_neo4j_repository_returns_json_safe_rows`
- `test_recommendation_analyze_does_not_500_on_neo4j_datetime`

## 9. Test result

```text
pytest -q → 107 passed, 1 skipped, 1 warning
```

## 10. Ruff result

```text
ruff check . → passed
```

## 11. MyPy result

```text
mypy app → passed, 144 source files
```

## 12. Compile result

```text
python -m compileall app → passed
```

## 13. Successful response example

```json
{
  "status": "completed",
  "complaint": "batuk berdahak dan tenggorokan gatal selama dua hari",
  "recommendations": [
    {
      "local_name": "Kencur",
      "evidence_sources": [
        {
          "updated_at": "2026-06-18T12:00:00"
        }
      ]
    }
  ]
}
```

## 14. Remaining errors
- Manual PowerShell/curl not run because valid user token was not provided.
- No remaining backend test/ruff/mypy failures.
