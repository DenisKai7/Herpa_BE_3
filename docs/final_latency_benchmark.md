# Final Latency Benchmark

Run:

```powershell
python .\scripts\benchmark_final_modes.py
```

Outputs:

- `docs/final_benchmark_after.json`
- `docs/final_benchmark_after.csv`

The script writes incrementally after every row. Long llama.cpp rows can be stopped without losing completed measurements.

Known measured partial data from prior benchmark:

| Mode | Persona | Direct | Model calls | Total ms |
|---|---|---:|---:|---:|
| fast-medium | umum | true | 0 | 1606 |
| fast-medium | pelajar | true | 0 | 8 |
| fast-medium | peneliti | true | 0 | 15 |
| thinking-high | umum | false | 1 | 175206 |
| thinking-high | pelajar | false | 1 | 123117 |

Conclusion: direct fast-medium meets 0-call target; thinking-high latency remains llama.cpp/hardware-bound.
