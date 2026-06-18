# HERBAL RECOMMENDATION QUALITY FIX REPORT

## 1. Penyebab `NaN%`
Frontend menghitung persentase dari field yang tidak selalu dikirim backend (`recommendation_score`, `symptom_coverage`, `scores.*`). `Math.round(undefined * 100)` menghasilkan `NaN%`.

## 2. Penyebab label `Tidak aman`
Frontend menjadikan `undefined safety_status` sebagai fallback cabang merah/unsafe. Data safety kosong ikut tampil sebagai `Tidak aman`.

## 3. Penyebab penjelasan kosong
Backend mengirim `reason`, sementara frontend membaca `recommendation_reason` atau `explanation`. Akibatnya UI menampilkan fallback `Penjelasan belum tersedia dari backend.`

## 4. Backend files changed
- `app/models/recommendation.py`
- `app/logic/recommendation_orchestrator.py`
- `app/graph/repositories.py`
- `app/services/recommendation/__init__.py`
- `app/services/recommendation/symptom_aliases.py`
- `tests/contract/test_recommendation_quality.py`
- `docs/herbal_recommendation_quality_audit.md`
- `docs/herbal_recommendation_scoring.md`
- `docs/herbal_recommendation_safety_policy.md`
- `docs/herbal_recommendation_frontend_rendering.md`

## 5. Frontend files changed
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\app\recommendation\page.tsx`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\lib\api\herbalRecommendation.ts`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\lib\api\herbalRecommendation.contract.test.ts`

## 6. Schema response final
Primary field: `recommendations`.
Compatibility field: `options`, always synced to `recommendations`.

Candidate fields include:
- `confidence`
- `relevance_score`
- `recommendation_score`
- `relevance_level`
- `relevance_label`
- `safety_status`
- `safety_label`
- `safety_notes`
- `evidence_status`
- `evidence_label`
- `explanation`
- `recommendation_reason`
- `match_reasons`
- `related_symptoms`
- `active_compounds`
- `scores`

## 7. Formula scoring final

```text
confidence =
  symptom_match_score * 0.40
  + alias_match_score * 0.20
  + compound_score * 0.15
  + evidence_score * 0.15
  + safety_score * 0.10
```

All score values are clamped to `0.0–1.0` by `clamp_score()`.

## 8. Mapping safety status final
- `safe` → `Relatif aman`
- `caution` → `Perlu perhatian`
- `unsafe` → `Tidak aman`
- `unknown` → `Data keamanan belum cukup`

Empty safety data maps to `unknown`, not `unsafe`.

## 9. Mapping evidence status final
- no source → `unavailable` / `Data bukti belum tersedia`
- one source → `limited` / `Data bukti terbatas`
- two or more sources → `available` / `Data pendukung tersedia`

## 10. Mapping relevance label final
- `>= 0.75` → `high` / `Relevansi tinggi`
- `>= 0.50` → `medium` / `Relevansi sedang`
- `> 0` → `low` / `Relevansi rendah`
- `0` → `unknown` / `Relevansi belum tersedia`

## 11. Alias gejala yang ditambahkan
- `batuk berdahak`: `batuk`, `dahak`, `ekspektoran`, `mukolitik`, `saluran pernapasan`, `radang tenggorokan`
- `tenggorokan gatal`: `tenggorokan`, `iritasi tenggorokan`, `radang tenggorokan`, `batuk`, `antiinflamasi`
- `batuk`: `batuk`, `ekspektoran`, `saluran pernapasan`
- `pilek`: `pilek`, `flu`, `hidung tersumbat`
- `mual`: `mual`, `antiemetik`, `pencernaan`
- `perut kembung`: `kembung`, `karminatif`, `pencernaan`

## 12. Contoh response baru

```json
{
  "status": "completed",
  "complaint": "batuk berdahak dan tenggorokan gatal",
  "symptoms": ["batuk berdahak", "tenggorokan gatal"],
  "recommendations": [
    {
      "local_name": "Kencur",
      "scientific_name": "Kaempferia galanga L.",
      "confidence": 0.42,
      "relevance_score": 0.42,
      "relevance_level": "low",
      "relevance_label": "Relevansi rendah",
      "safety_status": "unknown",
      "safety_label": "Data keamanan belum cukup",
      "evidence_status": "limited",
      "evidence_label": "Data bukti terbatas",
      "explanation": "Kencur muncul sebagai kandidat awal, tetapi relevansinya masih rendah sehingga perlu verifikasi lebih lanjut.",
      "match_reasons": ["Keluhan yang dianalisis: batuk berdahak, tenggorokan gatal."],
      "warnings": ["Gunakan informasi ini sebagai edukasi awal, bukan pengganti pemeriksaan tenaga kesehatan."]
    }
  ],
  "when_to_seek_medical_help": [
    "Segera periksa ke tenaga kesehatan jika batuk disertai sesak napas, demam tinggi, nyeri dada, dahak berdarah, atau berlangsung lebih dari 3 hari."
  ],
  "safety_note": "Informasi ini bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan."
}
```

## 13. Hasil backend test
- `python -m compileall app` → passed
- `ruff check .` → passed
- `mypy app` → passed
- `pytest -q` → `97 passed, 1 skipped, 1 warning`

## 14. Hasil frontend build
- `npm --prefix /d/UNV/kuliah/skripsi/Denis/program/medical_ai_frontend run build` → passed

## 15. Error tersisa
- `npm --prefix /d/UNV/kuliah/skripsi/Denis/program/medical_ai_frontend run lint` still fails on unrelated pre-existing admin/profile/quiz/chat files.
- No manual browser/curl run because no live valid auth token was provided.
