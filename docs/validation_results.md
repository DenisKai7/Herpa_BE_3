# Validation Results

Validation executed in the artifact environment on 17 June 2026.

| Check | Result |
|---|---|
| `python -m compileall -q app data_pipeline scripts` | PASS |
| `ruff check .` | PASS |
| `mypy app` | PASS — 126 source files |
| `pytest -q` | PASS — 14 tests |
| `python -m scripts.check_secrets` | PASS — no obvious committed secrets |
| FastAPI OpenAPI export | PASS — 61 paths, 65 operations |
| `docker-compose.yml` YAML parse | PASS — 5 services |
| `docker-compose.gpu.yml` YAML parse | PASS — 2 services |

## Environment limitations

Docker CLI was not installed, so `docker compose config`, image build, and container startup were not executed. Cloud integration tests also require the user's Supabase, Neo4j, MinIO, model files, and credentials. The public repositories were audited through GitHub source views; direct Git clone from the container failed because `github.com` DNS resolution was unavailable.
