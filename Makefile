.PHONY: install dev test lint typecheck run docker-up docker-down seed graph-seed
install:
	python -m pip install -e ".[dev]"
dev:
	ALLOW_MOCK_SERVICES=true uvicorn app.main:app --reload
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000
test:
	APP_ENV=test ALLOW_MOCK_SERVICES=true pytest
lint:
	ruff check .
typecheck:
	mypy app
docker-up:
	docker compose --profile ai up -d --build
docker-down:
	docker compose down
seed:
	python -m scripts.seed
graph-seed:
	python -m data_pipeline.ingest_neo4j
