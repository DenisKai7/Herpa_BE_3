# Herbal Recommendation Quality Audit

## Issue
Endpoint returned 200, but UI rendered poor-quality recommendation labels: `NaN%`, false `Tidak aman`, missing explanation, and unclear evidence/relevance labels.

## Root causes

### NaN score
Frontend used `recommendation_score`, `symptom_coverage`, and nested `scores` fields that backend did not always send. `Math.round(undefined * 100)` produced `NaN%`.

### False unsafe label
Frontend treated missing `safety_status` as the unsafe fallback. Empty safety data was therefore displayed as `Tidak aman`.

### Missing explanation
Backend returned `reason`, while frontend rendered `recommendation_reason` / `explanation`. Missing mapping produced `Penjelasan belum tersedia dari backend.`

### Evidence/relevance ambiguity
Backend did not provide stable labels (`relevance_label`, `safety_label`, `evidence_label`), so frontend inferred labels from incomplete fields.

## Files audited
- `app/models/recommendation.py`
- `app/logic/recommendation_orchestrator.py`
- `app/graph/repositories.py`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\app\recommendation\page.tsx`
- `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\lib\api\herbalRecommendation.ts`

## Fix summary
- Backend now emits stable numeric scores and labels.
- Empty safety data maps to `unknown`, not `unsafe`.
- Empty evidence maps to `unavailable`.
- Backend emits `explanation` and `match_reasons`.
- Frontend uses `formatPercent()` to prevent `NaN%`.
- Frontend uses backend labels instead of unsafe fallback inference.
