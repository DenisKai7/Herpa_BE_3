# MODEL MODES IMPLEMENTATION REPORT

## Ringkasan
- Ditambahkan `ModelMode`: `fast-medium`, `thinking-hard`.
- Persona tetap terpisah dari model mode.
- llama.cpp dipanggil via OpenAI-compatible `/v1/models` dan `/v1/chat/completions`.
- Error model tidak lagi dibuang menjadi generic 503; error code masuk response/details.
- Circuit breaker memiliki `closed/open/half-open` dan bisa pulih setelah cooldown.
- Vision disabled tidak menggagalkan readiness.
- ORJSONResponse deprecated usage di app code dihapus.

## Penyebab 503 sebenarnya
Dari alur log: auth/profile/chat/user message sukses; gagal setelah masuk GraphRAG/model. Titik rawan: llama.cpp text server unreachable, timeout, model id mismatch, context overflow, atau circuit breaker open. Implementasi baru mengekspos kode: `TEXT_MODEL_UNAVAILABLE`, `TEXT_MODEL_TIMEOUT`, `MODEL_OUTPUT_INVALID`, `MODEL_CONTEXT_OVERFLOW`.

## File utama diubah
- `app/core/constants.py`
- `app/core/model_modes.py`
- `app/core/config.py`
- `app/core/exceptions.py`
- `app/main.py`
- `app/models/chat.py`
- `app/api/v1/chats.py`
- `app/api/v1/health.py`
- `app/logic/chat_orchestrator.py`
- `app/agents/state.py`
- `app/agents/graph.py`
- `app/agents/graph_retriever_agent.py`
- `app/graph/retriever.py`
- `app/services/ai/text_client.py`
- `app/services/ai/model_gateway.py`
- `app/services/ai/context_budget.py`
- `app/prompts/model_modes.py`
- `.env.example`

## File dibuat
- `docs/model_mode_fix_audit.md`
- `docs/model_modes.md`
- `scripts/diagnose_runtime.py`
- `tests/unit/test_model_modes.py`

## Struktur model mode
```python
class ModelMode(StrEnum):
    FAST_MEDIUM = "fast-medium"
    THINKING_HARD = "thinking-hard"
```

## Request/response
Request:
```json
{"message":"Jelaskan manfaat jahe","ai_mode":"umum","model_choice":"fast-medium"}
```
Success response berisi envelope `success/data/meta` plus field legacy top-level (`chat_id`, `response`) untuk kompatibilitas test/API lama.

## Health check lokal
- `GET http://127.0.0.1:8080/v1/models`: PASS, model `Qwen3-4B-Instruct-2507` tersedia.
- `GET http://127.0.0.1:8000/api/v1/health/models`: PASS untuk text, circuit `closed`, resolved model benar.
- Catatan: `.env` lokal masih `ENABLE_VISION=true`; vision health false jika VLM tidak berjalan. Set `ENABLE_VISION=false` untuk mode lokal text-only.

## Validasi
- `python -m compileall app`: PASS
- `ruff check .`: PASS
- `mypy app`: PASS
- `pytest -q`: PASS (`30 passed`, 1 warning Starlette/httpx testclient)
- `ruff format --check .`: PASS (`156 files already formatted`)

## Cara menjalankan llama-server
```powershell
llama-server -m app/models/Qwen_Qwen3-4B-Instruct-2507-Q6_K.gguf --host 127.0.0.1 --port 8080 --ctx-size 4096
```

## Cara menjalankan backend
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Checklist acceptance
- Legacy endpoint: done.
- `/api/v1` endpoint: done.
- Persona/model mode separated: done.
- Alias persona/model: done.
- Model auto-discovery: done.
- Circuit breaker recovery: done.
- Context budgeting: done.
- Vision disabled readiness behavior: done.
- SSE event mode metadata: done.
- No CoT prompt/output instruction: done.
- Tests/lint/type/format: pass.
- No secrets added: done.
