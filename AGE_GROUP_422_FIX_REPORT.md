# AGE_GROUP 422 Fix Report

## Penyebab
Backend `HerbalRecommendationRequest.age_group` sebelumnya memakai literal ketat. Frontend mengirim `age_group: "unknown"`, sehingga Pydantic menolak request sebelum endpoint berjalan dan mengembalikan HTTP 422 `literal_error` pada `body.age_group`.

## Nilai frontend sebelumnya

```json
{
  "age_group": "unknown",
  "pregnancy_status": "unknown"
}
```

## Schema request final

```json
{
  "complaint": "batuk berdahak dan tenggorokan gatal",
  "symptoms": [],
  "persona": "umum",
  "model_choice": "fast-medium",
  "age_group": null,
  "pregnancy_status": null,
  "allergies": [],
  "current_medications": [],
  "medical_conditions": []
}
```

## Mapping age_group

- `anak`, `anak-anak`, `child`, `children`, `infant`, `bayi` → `child`
- `remaja`, `teen`, `teenager`, `adolescent` → `teen`
- `dewasa`, `adult`, `adults` → `adult`
- `lansia`, `lanjut usia`, `elderly`, `senior`, `tua` → `elderly`
- `""`, `null`, `"null"`, `"undefined"`, `"unknown"` → `null`

## Backend files changed

- `app/models/recommendation.py`
- `app/logic/recommendation_orchestrator.py`
- `app/main.py`
- `tests/contract/test_recommendation_schema.py`
- `docs/herbal_recommendation_age_group_fix_audit.md`
- `docs/herbal_recommendation_request_contract.md`

## Frontend files changed

- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\app\recommendation\page.tsx`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\lib\api\herbalRecommendation.ts`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\lib\api\herbalRecommendation.contract.test.ts`

## Tests added

Backend:

- `test_age_group_accepts_null`
- `test_age_group_accepts_empty_string`
- `test_age_group_accepts_dewasa_alias`
- `test_age_group_accepts_adult`
- `test_age_group_rejects_invalid_value_with_clear_error`
- `test_recommendation_request_accepts_complaint_only`
- `test_recommendation_request_accepts_legacy_keluhan`
- `test_recommendation_request_accepts_message_alias`
- `test_recommendation_empty_optional_fields_do_not_422`
- `test_validation_error_response_shape`

Frontend contract test helpers:

- `recommendation_payload_converts_empty_age_group_to_null`
- `recommendation_payload_uses_canonical_age_group_values`
- `recommendation_error_parser_shows_validation_detail`

## Verification results

- `python -m compileall app` → passed
- `ruff check .` → passed
- `mypy app` → passed
- `pytest -q` → `83 passed, 1 skipped, 1 warning`
- `npm --prefix /d/UNV/kuliah/skripsi/Denis/program/medical_ai_frontend run build` → passed
- `npm --prefix /d/UNV/kuliah/skripsi/Denis/program/medical_ai_frontend run lint` → failed on pre-existing unrelated lint errors in admin/profile/quiz/chat files. Related `herbalRecommendation.ts` lint issue fixed.

## Successful payload example

```json
{
  "complaint": "batuk berdahak dan tenggorokan gatal",
  "age_group": null,
  "pregnancy_status": null,
  "allergies": [],
  "current_medications": [],
  "medical_conditions": []
}
```

## Successful no-match response behavior

```json
{
  "status": "no_fully_verified_candidate",
  "recommendations": [],
  "warnings": [
    "Data knowledge graph belum menemukan rekomendasi herbal yang cukup kuat untuk keluhan ini."
  ],
  "safety_note": "Informasi ini bersifat edukatif dan bukan pengganti pemeriksaan tenaga kesehatan."
}
```

## Remaining errors

Frontend lint still has unrelated pre-existing failures outside herbal recommendation flow, including:

- `src/app/admin/page.tsx`: `react-hooks/set-state-in-effect`
- `src/app/profile/page.tsx`: `react-hooks/set-state-in-effect`
- `src/app/quiz/session/page.tsx`: `no-explicit-any`, conditional hook
- `src/app/quiz/summary/page.tsx`: forbidden `require()`
- quiz/chat components: existing `no-explicit-any` and hook dependency issues
