# RUNTIME ERROR FIX IMPLEMENTATION REPORT

## 1. Penyebab Error Awal
- **Missing Fulltext Index**: Query templates menggunakan `db.index.fulltext.queryNodes` untuk mencari node tanaman. Ketika index `herb_fulltext_idx` belum teralokasikan atau offline di Aura DB, query tersebut melempar procedure exception yang membungkus error sebagai `NEO4J_UNAVAILABLE` dan menghentikan alur GraphRAG.
- **llama.cpp HTTP 400 Mappings**: Semua bad request (HTTP 400) dari server local `llama-server` langsung dianggap sebagai context overflow (status 413) tanpa membedakan parameter unsupported, model name alias mismatch, atau bad formats.
- **Frontend Request Bloat**: Initial Next.js page mount memicu pemanggilan `initialize()` dari `useAuthStore` dan `fetchSessions()` dari `useChatStore` berkali-kali secara konkuren.

## 2. Penyebab Asli HTTP 400 llama.cpp
Setelah dianalisis, HTTP 400 terjadi akibat:
- build llama.cpp tidak mendukung parameter sampling tertentu (`top_k`, `min_p`, `repeat_penalty`, dll.) atau parameter optimizer seperti `cache_prompt`.
- Model name mismatch (ID model berbeda antara config `.env` dan slot actual yang terload).

## 3. Laporan Validasi
- `python -m compileall app` → PASS
- `ruff check .` → PASS
- `mypy app` → PASS
- `pytest -q` → PASS (56 passed)
- Next.js frontend build (`npm run build`) → PASS (Turbopack compiled successfully in 5.0s, TS/Lint passed).

## 4. File Diubah
- `app/core/config.py` (tambah cache TTL model metadata)
- `app/graph/query_templates.py` (tambah property search fallback)
- `app/graph/repositories.py` (implementasi GqlError fallback + status checker)
- `app/graph/retriever.py` (kirim persona parameter ke normalizer)
- `app/agents/graph.py` (update model call count & fit_messages_to_context parameters)
- `app/agents/graph_retriever_agent.py` (kirim persona ke retriever)
- `app/services/ai/text_client.py` (http 400 body parser + payload sanitizer & retry)
- `app/services/ai/model_gateway.py` (resolved model name metadata cache)
- `app/graph/compound_normalizer.py` (IUPAC hiding untuk persona umum)
- `database/neo4j/performance_indexes.cypher` (verification queries)
- `medical_ai_frontend/src/hooks/useAuthStore.ts` (deduplikasi in-flight promise auth)
- `medical_ai_frontend/src/hooks/useChatStore.ts` (deduplikasi in-flight promise chat sessions)

## 5. Laporan Diagnostic & Benchmark Chat Modes
- `python .\scripts\diagnose_chat_runtime.py` → PASS (Semua check OK).
- `python .\scripts\benchmark_chat_modes.py` → PASS (Baseline retrieval benchmarking sukses dalam 9307ms).
