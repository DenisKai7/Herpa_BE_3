# Herbal Recommendation Lazy Detail

New endpoint:

```text
GET /api/herbal-recommendations/herbs/{herb_id}/detail
```

Alias:

```text
GET /api/v1/recommendations/herbs/{herb_id}/detail
```

Response:

```json
{
  "status": "completed",
  "herb_id": "...",
  "detail": {},
  "disclaimer": "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
}
```

Frontend should call this only when user opens detail drawer/modal. If detail fails, keep candidate card visible and show safe fallback.
