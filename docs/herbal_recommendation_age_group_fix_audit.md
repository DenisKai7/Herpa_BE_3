# Herbal Recommendation Age Group 422 Audit

## Endpoint
- `POST /api/herbal-recommendations/analyze`
- Handler: `app/api/v1/recommendations.py`
- Request model: `app/models/recommendation.py::HerbalRecommendationRequest`

## Root cause
Frontend sent `age_group: "unknown"`. Backend previously accepted only `Literal["child", "adolescent", "adult", "elderly"]`, so Pydantic rejected the request before endpoint logic ran.

## Observed frontend payload
File: `D:\UNV\kuliah\skripsi\Denis\program\medical_ai_frontend\src\app\recommendation\page.tsx`

Previous payload included:

```json
{
  "complaint": "...",
  "age_group": "unknown",
  "pregnancy_status": "unknown",
  "allergies": [],
  "chronic_conditions": [],
  "current_medications": []
}
```

## Backend audit
- `app/models/recommendation.py`: rigid `age_group` literal caused `literal_error`.
- `app/logic/recommendation_orchestrator.py`: used `symptoms` + `free_text`; complaint-only input needed normalization into analysis text.
- `app/main.py`: only `AppError` handler existed; FastAPI validation errors used default `detail[]` body.
- `app/core/exceptions.py`: app error shape uses `{success:false,error:{code,message,details},meta}`.

## Frontend audit
- API client: `medical_ai_frontend/src/lib/api/herbalRecommendation.ts`
- Page caller: `medical_ai_frontend/src/app/recommendation/page.tsx`
- Error display previously combined code + generic HTTP message, causing `HERBAL_RECOMMENDATION_FAILED: Request gagal dengan HTTP 422`.

## Fix summary
- `age_group` now optional and normalized.
- Empty string, `null`, `undefined`, `unknown` become `None/null`.
- Indonesian/English aliases accepted.
- Frontend sends `null`, not `unknown` or empty string.
- 422 response shape standardized.
