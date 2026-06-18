# Latency Benchmark

Run:

```powershell
python .\scripts\benchmark_compound_queries.py
```

Outputs:

- `benchmarks/compound_queries_latest.json`
- `benchmarks/compound_queries_latest.csv`

## Actual partial benchmark on 2026-06-17

Full benchmark was stopped because `thinking-high` llama.cpp rows exceeded practical runtime on this device. Script now writes each row incrementally, so partial measurements are real and preserved.

| Query | Persona | Mode | Direct | Model calls | Retrieval ms | Generation ms | Total ms | Finish |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| senyawa di dalam kelor apa aja? | umum | fast-medium | true | 0 | 1603 | 0 | 1606 | complete |
| senyawa di dalam kelor apa aja? | umum | thinking-high | false | 1 | 185 | 175014 | 175206 | stop |
| senyawa di dalam kelor apa aja? | pelajar | fast-medium | true | 0 | 2 | 0 | 8 | complete |
| senyawa di dalam kelor apa aja? | pelajar | thinking-high | false | 1 | 1230 | 121874 | 123117 | length |
| senyawa di dalam kelor apa aja? | peneliti | fast-medium | true | 0 | 2 | 0 | 15 | complete |

## Notes

- Fast-medium direct path reached 0 model calls.
- Warm-cache fast-medium latency was 8-15 ms; cold first query was 1606 ms.
- Thinking-high remained model-bound: 121-175 s per completed row.
- A `finish_reason=length` row confirms why safe continuation is needed; runtime now detects `length` and performs at most one short continuation.
