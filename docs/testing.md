# Testing

```bash
python -m pip install -e ".[dev]"
APP_ENV=test ALLOW_MOCK_SERVICES=true pytest
ruff check .
mypy app
python -m compileall app data_pipeline scripts
docker compose config
```

Integration test cloud membutuhkan credential test terpisah dan tidak dijalankan secara default.
