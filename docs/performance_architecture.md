# Performance Architecture HERPA

Sistem dioptimalkan untuk mencapai throughput maksimal, latensi rendah, dan zero Cartesian explosion pada query Neo4j.

```text
Request JWT
  │
  ├── Local JWT Caching (30s) ──> Return auth payload
  │
  ├── Profile Cache (30s) ──> Return Profile & Persona
  │
  └── Chat API Route (FastAPI)
        │
        └── ChatOrchestrator.stream()
              │
              ├── Create asyncio.Queue & task AgenticGraph.run()
              │
              ├── Step 1: Rule-based ComplexityAssessment
              │     │
              │     ├── Fast Medium: limit = 1, no targets, no refinement.
              │     └── Thinking High: limit = 2, targets & tools if complex, conditional refinement.
              │
              ├── Step 2: Parallel Split Neo4j Queries (asyncio.gather)
              │     │
              │     ├── Cache Lookup (AsyncMemoryTTLCache)
              │     └── managed_read_transaction (Retry on SessionExpired)
              │
              ├── Step 3: Stream draft tokens from llama.cpp
              │     │
              │     └── Put tokens directly into asyncio.Queue
              │
              └── Step 4: SSE reader reads queue and yields chunks
                    │
                    └── Batch Supabase message persistence once at completion
```

## Optimasi Kunci
1. **Deduplikasi Compound**: Menggunakan `CompoundNormalizer` berbasis nama normalized dan PubChem CID untuk membuang duplikat senyawa.
2. **Context Budgeting**: `ContextBudgeter` memotong chat history lama dan detail sekunder secara dinamis untuk menghemat limit context window.
3. **Common Prefix Caching**: Prompt diurutkan secara statis agar prefix cache pada `llama-server` tetap valid.
4. **Adaptive Refinement**: Refinement pass kedua pada `thinking-high` dihindari untuk pertanyaan sederhana.
