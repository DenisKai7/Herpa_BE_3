# Herbal Recommendation Request Contract

## Endpoint

`POST /api/herbal-recommendations/analyze`

## Minimal payload

```json
{
  "complaint": "batuk berdahak dan tenggorokan gatal"
}
```

## Full payload

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

## Defaults

- `symptoms`: `[]`
- `persona`: `"umum"`
- `model_choice`: `"fast-medium"`
- `age_group`: `null`
- `pregnancy_status`: `null`
- `allergies`: `[]`
- `current_medications`: `[]`
- `medical_conditions`: `[]`

## Complaint aliases

If `complaint` is missing, backend accepts:

- `keluhan`
- `main_complaint`
- `query`
- `message`
- `text`

## Age group canonical values

| UI label | Request value |
|---|---|
| Anak-anak | `child` |
| Remaja | `teen` |
| Dewasa | `adult` |
| Lansia | `elderly` |

## Age group aliases

- `anak`, `anak-anak`, `child`, `children`, `infant`, `bayi` → `child`
- `remaja`, `teen`, `teenager`, `adolescent` → `teen`
- `dewasa`, `adult`, `adults` → `adult`
- `lansia`, `lanjut usia`, `elderly`, `senior`, `tua` → `elderly`
- `""`, `null`, `"null"`, `"undefined"`, `"unknown"` → `null`

## Pregnancy status aliases

- `tidak`, `tidak hamil`, `not_pregnant` → `not_pregnant`
- `hamil`, `pregnant` → `pregnant`
- `menyusui`, `breastfeeding` → `breastfeeding`
- `tidak tahu`, `unknown` → `unknown`
- `""`, `null`, `"null"`, `"undefined"` → `null`

## Validation error shape

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Format request tidak sesuai.",
    "details": []
  },
  "meta": {
    "request_id": "..."
  }
}
```
