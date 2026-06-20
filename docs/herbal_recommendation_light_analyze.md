# Herbal Recommendation Light Analyze

Analyze now defaults to light mode via `HERBAL_RECOMMENDATION_LIGHT_ANALYZE=true`.

Flow:
1. Extract/expand symptom terms.
2. Query `HERBAL_RECOMMENDATION_LIGHT_BY_SYMPTOMS`.
3. If empty/error, query `HERBAL_RECOMMENDATION_LIGHT_LEGACY`.
4. Build `HerbalCandidate` with backward-compatible fields.
5. Do not load full enrichment while `HERBAL_RECOMMENDATION_LAZY_DETAIL=true`.

Timeout fallback returns `status=completed` with warnings/limitations instead of raw 500.
