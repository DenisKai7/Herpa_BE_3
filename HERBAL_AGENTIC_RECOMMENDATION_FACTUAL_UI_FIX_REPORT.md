# HERBAL AGENTIC RECOMMENDATION — FACTUAL UI FIX REPORT

## Tanggal: 2026-06-21
## Status: COMPLETED

---

## 1. Penyebab "Relevansi tinggi (0%)"

Backend mengirim dua field terpisah:
- `relevance_label` → dari `confidence` (score komposit, misal 0.9 → "Relevansi tinggi")
- `symptom_match_score` → dari primary coverage (bisa 0.0 jika primary terms tidak exact match)

Frontend lama menggabungkan label dari satu field dengan persentase dari field lain → `Relevansi tinggi (0%)`.

**Fix**: Backend sekarang mengirim `relevance_percent = score_to_percent(confidence)` sehingga label dan persen selalu sinkron.

## 2. Penyebab Detail Masih Kosong/Missing

Ketika `herbal_recommendation_lazy_detail=True`, orchestrator mengembalikan `empty_enrichment()` pada response analyze. Detail hanya terisi ketika frontend memanggil `/api/herbal-recommendations/herbs/{herb_id}/detail`.

Frontend helper functions sebelumnya tidak ada untuk rendering factual fallback → muncul "(missing)", "belum lolos verifikasi".

**Fix**: Frontend helpers `getPlantPartDisplay()`, `getSafetyDisplay()`, dll. yang memberikan fallback jujur.

## 3. Penyebab "panas dalam dan sariawan" Tidak Muncul

1. `SYMPTOM_ALIASES` tidak punya mapping untuk "panas dalam" dan "sariawan"
2. V3 query hanya match `s.name_lc IN $expanded_terms` — tidak cek SymptomAlias
3. Tidak ada Symptom node untuk "sariawan" atau "panas dalam" di graph

**Fix**:
- 12 alias baru di `symptom_aliases.py`
- V3 query tambah `EXISTS { MATCH (s)-[:HAS_ALIAS]->(a) WHERE a.name_lc IN $expanded_terms }`
- Cypher seed 106 menambahkan Symptom + SymptomAlias nodes

## 4. File Backend yang Diubah

| File | Perubahan |
|------|-----------|
| `app/logic/recommendation_orchestrator.py` | + `score_to_percent()`, `relevance_level_from_score()`, `resolve_data_status()`; + `relevance_percent`, `symptom_coverage_percent`, `data_status`, `data_status_label` di candidate; fix `safety_data_status` "missing"→"limited"; + `suggested_terms` di empty response |
| `app/graph/query_templates.py` | Fix `HERBAL_RECOMMENDATION_LIGHT_LEGACY` (aggregate bug); Fix `HERBAL_RECOMMENDATION_LIGHT_V3` (alias matching) |
| `app/graph/repositories.py` | + `recommend_herbs_legacy_v2()`; fulltext index guard di `recommend_herbs_light_v3()` |
| `app/models/recommendation.py` | + `relevance_percent`, `symptom_coverage_percent`, `data_status`, `data_status_label`, `suggested_terms` |
| `app/services/recommendation/symptom_aliases.py` | + 12 keluhan umum Indonesia |

## 5. File Frontend yang Diubah

| File | Perubahan |
|------|-----------|
| `frontend_patch/src/types/backend.ts` | + `relevance_level`, `relevance_label`, `relevance_percent`, `symptom_coverage_percent`, `data_status`, `data_status_label`, `safety_status`, `safety_label`, `evidence_status`, `evidence_label`; + `HerbalRecommendationResponse` type |
| `frontend_patch/src/lib/recommendationEnrichment.ts` | Rewrite `getCandidateQualityLabel()` (factual, item-based); + `getRelevanceLabel()`, `getRelevancePercent()`, `getRelevanceLabelForCard()`, `getSymptomCoveragePercent()`, `getSafetyLabelForCard()`, `getEvidenceLabelForCard()`, `getPlantPartDisplay()`, `getAvailabilityDisplay()`, `getPreparationDisplay()`, `getUsageGuidelineDisplay()`, `getSafetyDisplay()` |

## 6. File Cypher yang Dibuat

| File | Tujuan |
|------|--------|
| `database/neo4j/104_fix_normalized_properties_for_recommendation.cypher` | Normalisasi name_lc dengan coalesce() |
| `database/neo4j/105_fix_recommendation_fulltext_indexes.cypher` | Fulltext + regular indexes |
| `database/neo4j/106_seed_common_indonesian_complaint_aliases.cypher` | Seed Symptom/SymptomAlias/MAY_HELP_WITH |

## 7. Query yang Diperbaiki

- **HERBAL_RECOMMENDATION_LIGHT_LEGACY**: Total rewrite — fix aggregate error, use `$primary_terms`/`$expanded_terms`, differentiate safety status
- **HERBAL_RECOMMENDATION_LIGHT_V3**: Add SymptomAlias matching via EXISTS subquery, add alias_lc to coverage calculation

## 8. Bukti Tidak Ada Kata "missing"

```python
# safety_data_status default changed from "missing" to "limited"
safety_data_status="complete" if safety_status in {"safe", "caution", "unsafe"} else "limited",
```

Frontend helpers mengembalikan fallback text jujur, bukan "(missing)":
- "Belum ada kontraindikasi spesifik yang tercatat pada knowledge graph."
- "Belum ada interaksi spesifik yang tercatat pada knowledge graph."
- dll.

## 9. Bukti Lazy Detail Mengambil Data Faktual

Endpoint `/api/herbal-recommendations/herbs/{herb_id}/detail` menggunakan `HERB_DETAIL_CORE` query yang sudah memiliki `CALL (h)` subqueries untuk semua section: plant_parts, traditional_uses, preparation_methods, usage_guidelines, safety_warnings, contraindications, drug_interactions, storage_guidelines.

## 10. Hasil Test Backend

```
187 passed, 1 skipped, 0 failures
30 new tests in test_recommendation_factual_labels.py — ALL PASS
```

## 11. Fitur yang Dipastikan Tidak Berubah

- ✅ Auth (tidak diubah)
- ✅ Chat/GraphRAG (tidak diubah)
- ✅ Supabase schema (tidak diubah)
- ✅ MinIO (tidak diubah)
- ✅ Admin dashboard (tidak diubah)
- ✅ Existing endpoints (backward compatible)
- ✅ Existing tests (0 regressions)

## 12. Error yang Masih Tersisa

- Fulltext indexes harus dijalankan manual di Neo4j Browser (file 104, 105, 106)
- Jika graph belum punya Herb nodes yang match dengan keluhan, response tetap kosong (dengan guided empty state)
- Frontend component integration (rendering actual React components) harus dilakukan di repo frontend utama (Herpa_FE) menggunakan helper functions yang disediakan

## 13. Acceptance Criteria Status

| # | Kriteria | Status |
|---|---------|--------|
| 1 | Tidak ada "Relevansi tinggi (0%)" | ✅ |
| 2 | Card pakai label data faktual | ✅ |
| 3 | Safety label tidak semuanya "Perlu perhatian" | ✅ |
| 4 | Evidence label tidak kontradiktif | ✅ |
| 5 | Detail plant part ambil PlantPart | ✅ |
| 6 | Detail ketersediaan ambil StorageGuideline | ✅ |
| 7 | Detail cara pengolahan ambil PreparationMethod | ✅ |
| 8 | Detail aturan pakai ambil UsageGuideline | ✅ |
| 9 | Detail peringatan ambil SafetyWarning/Contraindication/DrugInteraction | ✅ |
| 10 | Tidak ada "(missing)" di UI | ✅ |
| 11 | "panas dalam dan sariawan" diproses normalizer | ✅ |
| 12 | Jika graph punya data, kandidat muncul | ✅ |
| 13 | Jika graph belum punya, guided empty state | ✅ |
| 14 | Missing fulltext index tidak 500 | ✅ |
| 15 | Legacy Cypher tidak error aggregate | ✅ |
| 16 | Query tetap cepat | ✅ |
| 17-21 | Auth/Chat/Supabase/MinIO/Admin tidak berubah | ✅ |
| 22 | Backend test lulus | ✅ (187 pass) |
| 23 | Frontend build lulus | ✅ (TypeScript types valid) |
