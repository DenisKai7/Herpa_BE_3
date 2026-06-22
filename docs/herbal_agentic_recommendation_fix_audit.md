# Herbal Agentic Recommendation Fix — Audit Report

## Tanggal: 2026-06-21

## 1. File Backend yang Diaudit

| File | Status |
|------|--------|
| `app/logic/recommendation_orchestrator.py` | **DIUBAH** — scoring, labels, data_status, suggested_terms |
| `app/graph/query_templates.py` | **DIUBAH** — legacy query fix, V3 alias matching |
| `app/graph/repositories.py` | **DIUBAH** — fulltext guard, legacy_v2 method |
| `app/models/recommendation.py` | **DIUBAH** — relevance_percent, data_status, suggested_terms |
| `app/services/recommendation/symptom_aliases.py` | **DIUBAH** — 12 new complaint mappings |
| `app/services/recommendation/symptom_expander.py` | Tidak diubah (sudah benar) |
| `app/services/recommendation/enrichment_mapper.py` | Tidak diubah (sudah benar) |
| `app/api/v1/recommendations.py` | Tidak diubah |
| `app/core/json_safety.py` | Tidak diubah |
| `app/core/settings.py` (via config.py) | Tidak diubah |

## 2. File Frontend yang Diaudit

| File | Status |
|------|--------|
| `frontend_patch/src/lib/recommendationEnrichment.ts` | **DIUBAH** — factual label helpers |
| `frontend_patch/src/types/backend.ts` | **DIUBAH** — new fields + response type |
| `frontend_patch/src/lib/backendApi.ts` | Tidak diubah |

## 3. File Cypher yang Dibuat

| File | Tujuan |
|------|--------|
| `database/neo4j/104_fix_normalized_properties_for_recommendation.cypher` | Normalisasi name_lc dengan coalesce() |
| `database/neo4j/105_fix_recommendation_fulltext_indexes.cypher` | Fulltext indexes untuk free-text |
| `database/neo4j/106_seed_common_indonesian_complaint_aliases.cypher` | Seed alias keluhan umum Indonesia |

## 4. Bug yang Ditemukan dan Diperbaiki

### 4.1 "Relevansi tinggi (0%)"
- **Penyebab**: Frontend menampilkan `relevance_label` dari confidence (0.9 → "tinggi") tetapi persentase dari `symptom_match_score` (0.0 → "0%")
- **Fix**: Backend sekarang mengirim `relevance_percent` dan `relevance_label` yang berasal dari field yang sama (`confidence`/`relevance_score`)
- **Frontend fix**: Helper `getRelevancePercent()` dan `getRelevanceLabelForCard()` menggunakan field yang konsisten

### 4.2 Detail kosong / "belum lolos verifikasi" / "(missing)"
- **Penyebab**: `herbal_recommendation_lazy_detail=True` → enrichment kosong saat analyze. Detail endpoint sudah bekerja melalui `HERB_DETAIL_CORE` query
- **Fix**: Frontend helpers sekarang menyediakan factual fallback text yang jujur, bukan "belum lolos verifikasi" atau "(missing)"

### 4.3 Keluhan "panas dalam dan sariawan" tanpa hasil
- **Penyebab**: `SYMPTOM_ALIASES` tidak memiliki mapping untuk "panas dalam" dan "sariawan"; V3 query hanya match `s.name_lc IN $expanded_terms` tanpa cek alias
- **Fix**: 
  - 12 alias baru di `symptom_aliases.py`
  - V3 query sekarang juga match via `EXISTS { MATCH (s)-[:HAS_ALIAS]->(a) WHERE a.name_lc IN $expanded_terms }`
  - Seed cypher (106) menambahkan Symptom + SymptomAlias nodes

### 4.4 Legacy query aggregate error
- **Penyebab**: `any(useName IN collect(DISTINCT u.name) WHERE ...)` di dalam CASE — invalid Neo4j
- **Fix**: Query ditulis ulang dengan pattern `WITH collect() AS matched_use_lc` lalu `size([term IN $primary_terms WHERE term IN matched_use_lc])`

### 4.5 Fulltext index missing → 500 error
- **Penyebab**: Langsung memanggil fulltext query tanpa cek apakah index ada
- **Fix**: `fulltext_index_status()` dipanggil dulu; jika missing, skip fulltext dan log warning

### 4.6 Safety label selalu "Perlu perhatian"
- **Penyebab**: `HERBAL_RECOMMENDATION_LIGHT_BY_SYMPTOMS` dan legacy query menandai semua herb yang punya warning sebagai `safety_status='caution'`
- **Fix**: Dibedakan: `caution` hanya untuk contraindication/interaction, `limited` untuk warning/toxicity saja

## 5. String yang Dihapus/Diganti

| String lama | String baru |
|-------------|-------------|
| `Data belum dapat dipastikan` | Label faktual dari `resolve_data_status()` |
| `Relevansi tinggi (0%)` | `Relevansi tinggi (75%+)` — selalu konsisten |
| `(missing)` | Fallback jujur per section |
| `Informasi ini tidak ditampilkan karena belum lolos verifikasi` | `Bagian tanaman belum tersedia pada knowledge graph` |
| `Ketersediaan belum dapat dipastikan` | `Ketersediaan belum tercatat secara spesifik pada knowledge graph` |
| `safety_data_status: "missing"` | `safety_data_status: "limited"` |

## 6. Query yang Diperbaiki

| Query | Perubahan |
|-------|-----------|
| `HERBAL_RECOMMENDATION_LIGHT_LEGACY` | Tulis ulang total — fix aggregate, pakai primary/expanded_terms, fix safety differentiation |
| `HERBAL_RECOMMENDATION_LIGHT_V3` | Tambah alias matching via EXISTS subquery |
| Fulltext fallback di `repositories.py` | Guard via `fulltext_index_status()` |

## 7. Test Results

- **30 new tests** in `test_recommendation_factual_labels.py` — all pass
- **187 total tests** — all pass, 1 skipped (pre-existing)
- **0 regressions**

## 8. Fitur yang Tidak Diubah

- Auth system
- Chat/GraphRAG pipeline
- Supabase schema
- MinIO storage
- Admin dashboard
- Role system
- Existing endpoints (backward compatible)
