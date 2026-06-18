# Compound Query Optimization Report

Status: implementation in progress.

## Bottlenecks Found

- Fast-medium always entered GraphRAG + LLM path.
- Thinking-high could run draft + full refinement for simple questions.
- Retrieval hydrated broad graph context, including data not needed for compound-list questions.
- Generic formatter added broad insufficiency message.
- finish_reason was not persisted.

## Changes Implemented

- Rule-based intent classifier.
- Direct answer engine for simple graph-grounded intents.
- Compound normalizer with nutrient separation and IUPAC hiding.
- Complexity analyzer for adaptive thinking-high.
- Minimal herb/compound/source retrieval helpers.
- Model metadata cache default raised to 600s.
- Neo4j retry/timeout defaults tightened.
- finish_reason capture added.
- Benchmark script added.

## Validation

Run validation commands after tests are fixed:

```powershell
python -m compileall app
ruff check .
mypy app
pytest -q
python .\scripts\benchmark_compound_queries.py
```

Frontend:

```powershell
npm run lint
npm run build
```

Benchmark results should be copied into `docs/latency_benchmark.md` after runtime dependencies are available.
