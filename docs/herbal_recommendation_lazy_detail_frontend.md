# Herbal Recommendation Lazy Detail Frontend

Use:

```text
GET /api/herbal-recommendations/herbs/{herb_id}/detail
```

Backend logs:

```text
herbal_detail_stage detail_request_received
```

Frontend should call the endpoint when Detail opens, use loaded `detail.traditional_uses`, `detail.preparation_methods`, `detail.usage_guidelines`, `detail.safety_warnings`, and show loading before empty fallback.
