# Model modes HERPA

## Request
```json
{
  "message": "Jelaskan manfaat jahe",
  "ai_mode": "umum",
  "model_choice": "fast-medium"
}
```

- `ai_mode` / `persona`: gaya jawaban (`umum`, `pelajar`, `peneliti`, `tenaga_medis`).
- `model_choice`: cara backend memproses jawaban (`fast-medium`, `thinking-hard`).

## Alias
Model:
- `fast`, `medium`, `fast_medium` -> `fast-medium`
- `thinking`, `hard`, `thinking_hard` -> `thinking-hard`

Persona:
- `general` -> `umum`
- `student` -> `pelajar`
- `oeneliti`, `researcher` -> `peneliti`
- `medical` -> `tenaga_medis`

## fast-medium
Pipeline ringkas: auth -> profile -> persona -> intent/entity/safety -> Neo4j terbatas -> attachment -> 1x generation -> grounding -> formatting -> persist.

Default retrieval: `FAST_MEDIUM_RETRIEVAL_LIMIT=6`.
Default output: `FAST_MEDIUM_MAX_TOKENS=600`.

## thinking-hard
Backend multi-pass, bukan native reasoning model. Maksimal 2 pass:
1. Draft generation berbasis fakta Neo4j, evidence, attachment, safety.
2. Refinement generation untuk hapus klaim tak grounded, perbaiki struktur, tambahkan keterbatasan.

Tidak mengirim chain-of-thought/scratchpad ke frontend.
Jika refinement gagal tetapi draft aman dan grounded minimum, response memakai `execution_mode_used="thinking-hard-draft-only"`, `degraded=true`.

## Health
`GET /api/v1/health/models` mengembalikan status text model, model terkonfigurasi, model resolved, available models, circuit state, dan vision status.

## llama-server lokal
```powershell
llama-server -m app/models/Qwen_Qwen3-4B-Instruct-2507-Q6_K.gguf --host 127.0.0.1 --port 8080 --ctx-size 4096
```
