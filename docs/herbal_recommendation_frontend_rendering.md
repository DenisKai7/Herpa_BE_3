# Herbal Recommendation Frontend Rendering

## Percent formatting
Use `formatPercent(value)` for all score display.

- invalid / `NaN` / `Infinity` / `undefined` / `null` → `Belum tersedia`
- valid number → rounded percent

## Label policy
Frontend should prefer backend-provided labels:

- `relevance_label`
- `safety_label`
- `evidence_label`

## Safety fallback
Missing safety status maps to `unknown` and displays `Data keamanan belum cukup`, not `Tidak aman`.

## Explanation
Use:

1. `explanation`
2. `recommendation_reason`
3. `Alasan rekomendasi belum tersedia pada data saat ini.`

## Recommendations source
Render `response.recommendations` as primary. `options` is compatibility alias only.

## Candidate count text
Use “kandidat awal berdasarkan data knowledge graph”, not “memenuhi kriteria” for low-confidence candidates.
