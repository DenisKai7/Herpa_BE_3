# Graph Cache and Resilience

Neo4j access uses one async driver and managed `session.execute_read()`.

Retry catches transient connection failures only:

- `SessionExpired`
- `ServiceUnavailable`
- `TransientError`
- `ConnectionResetError`

Direct context cache keys:

- `herb:v3:{herb_id}:identity`
- `herb:v3:{herb_id}:compounds:{limit}`
- `herb:v3:{herb_id}:sources:{limit}`
- `herb:v3:{herb_id}:thinking-high:{compound_limit}:{source_limit}`

Fast-medium direct retrieves only herb identity, compounds, and sources for compound-list queries.
