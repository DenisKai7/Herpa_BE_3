# IMPLEMENTATION REPORT — HERPA Agentic GraphRAG Backend

## Status

Backend runnable telah dibuat sebagai proyek terpisah untuk diintegrasikan dengan `Herpa_FE`. Implementasi mengadaptasi separation of concerns A.L.I.S.A. ke domain herbal/farmasi/kimia, tanpa membawa domain pembelajaran Bahasa Jepang.

## Audit repository

- Referensi backend menunjukkan pola FastAPI modular, Neo4j knowledge graph, Supabase application database, local inference, data pipeline, tests, dan database orchestration.
- Frontend target menggunakan Next.js/React serta API modules untuk auth, chat, file, admin, recommendation, profile, shared chat, dan tipe kuis.
- Compatibility routes ditambahkan agar frontend tidak perlu dirombak sebelum migrasi ke `/api/v1`.

## Arsitektur final

- FastAPI API layer.
- Supabase Auth + PostgreSQL sebagai source of truth untuk user/application state.
- Neo4j sebagai source of truth untuk fakta GraphRAG.
- MinIO untuk private objects.
- llama.cpp OpenAI-compatible text dan VLM server terpisah.
- Explicit agent state machine dengan safety dan grounding.
- PubMed/PubChem tool adapters.
- Docker modular dengan CPU/GPU override.

## Komponen yang diimplementasikan

### Authentication/RBAC

- Supabase login/register/token verification.
- Mock auth untuk automated tests.
- Profile-backed role dan persona.
- `require_admin` dan active-account check.
- User ID tidak diterima dari body sebagai sumber otorisasi.

### Agentic GraphRAG

- Persona, intent, safety, evidence, specialist, and response agent modules.
- Entity resolver untuk tanaman/senyawa awal.
- Neo4j query templates dengan parameters.
- Graph context builder dan grounding validator.
- Source metadata untuk Neo4j, PubMed, PubChem, dan attachment.

### Chat

- Create/list/get/update/delete.
- Rename, pin/unpin.
- Message persistence.
- SSE event stream.
- Share token generation and SHA-256 storage.
- Legacy and `/api/v1` routes.

### Attachment

- Direct multipart upload.
- Presigned upload flow.
- MinIO private bucket.
- PDF/DOCX/XLSX/CSV/TXT/MD extraction.
- VLM path for images/scanned content.
- Quota check, MIME validation, safe key, status, and deletion.

### Recommendation

- Structured symptom input.
- Emergency/red-flag stop condition.
- Neo4j candidate retrieval.
- Contraindication/interactions exclusion.
- Evidence-level/source output.
- Session/result persistence and history CRUD.

### External tools

- PubMed ESearch/ESummary adapter.
- PubChem compound properties adapter.
- Persona/intent-controlled tool calls.
- Timeout/error normalization through shared HTTP client.

### Quiz

- Subject/module/level/question schema.
- Attempts and answer upsert.
- Scoring, skip handling, XP, unlock status, `analisis_performa`.
- History, soft deletion, progress.
- Initial chemistry seed.

### Admin

- Overview analytics.
- User listing/detail.
- Role/status update with audit.
- Feature/model usage.
- Audit logs.
- Dependency health and storage summary.

## Database deliverables

### Supabase

- Initial schema migration.
- Auth profile trigger.
- Updated-at triggers.
- RLS policies.
- Admin RPC functions.
- Quiz seed.

### Neo4j

- Unique constraints.
- Full-text indexes.
- Example herbal graph seed.
- Verification queries.
- JSON ingestion pipeline for eight plants.

## Docker services

- `backend`
- `minio`
- `minio-init`
- `llama-text`
- `llama-vlm`

Neo4j Aura dan Supabase cloud tidak dijalankan lokal.

## Verification performed

```text
python -m compileall -q app data_pipeline scripts  PASS
ruff check .                                      PASS
mypy app                                          PASS (126 source files)
pytest -q                                         PASS (14 tests)
FastAPI mock smoke flow                           PASS
OpenAPI generation                               PASS (61 paths / 65 operations)
```

## Verification not performed in this environment

- `docker compose config/build/up`, karena Docker CLI tidak tersedia pada execution environment.
- Real Supabase migration and RLS execution.
- Real Neo4j Aura connectivity/ingestion.
- Real MinIO upload lifecycle.
- Real llama.cpp inference using the three GGUF files.
- Live PubMed/PubChem integration tests.
- `npm run lint/build` against a cloned `Herpa_FE` working tree.

Repository public telah diaudit melalui file tree dan source views, tetapi clone Git tidak dapat dilakukan dari container karena DNS/network Git tidak tersedia. Oleh karena itu, perubahan frontend diberikan sebagai isolated patch dan compatibility API, bukan commit langsung pada working tree frontend.

## Important production checks

1. Pin llama.cpp image/build after testing Qwen text and Qwen3-VL/mmproj on target hardware.
2. Run all SQL migrations on a staging Supabase project.
3. Verify RLS using two user accounts and one admin account.
4. Replace example Neo4j data with validated/cited datasets.
5. Add clinical governance for dose, interaction, contraindication, and ICD-10 content.
6. Configure TLS, reverse proxy, secret manager, backups, rate limits, and log retention.
7. Execute frontend contract tests against actual Herpa_FE.

## Acceptance checklist

- [x] FastAPI project and OpenAPI.
- [x] Role/user persona models.
- [x] Supabase clients/migrations/RLS.
- [x] Neo4j GraphRAG client/schema/seed.
- [x] MinIO attachment service.
- [x] llama.cpp text/VLM adapters.
- [x] Agent state machine.
- [x] Chat CRUD/SSE/share.
- [x] Recommendation safety pipeline/history.
- [x] PubMed/PubChem tools.
- [x] Quiz levels/attempts/scoring/history/progress.
- [x] Admin endpoints/analytics/audit.
- [x] Docker CPU/GPU definitions.
- [x] Unit/contract/mock E2E tests.
- [x] Documentation and setup scripts.
- [ ] Real external-service integration tests (requires user environment).
- [ ] Real GGUF inference validation (requires model files and target hardware).
- [ ] Frontend production build after applying patch to actual clone.
