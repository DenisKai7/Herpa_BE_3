# SCORING V2 FORMULATION

Granular score calculation:
- `best_symptom_match_score` * 0.45
- `avg_symptom_match_score` * 0.15
- `traditional_use_score` * 0.15
- `compound_score` * 0.10 (scaled by number of compounds, `min(count/5, 1.0)`)
- `safety_score` * 0.15 (`{"safe": 1.0, "unknown": 0.6, "caution": 0.3, "unsafe": 0.0}`)

Yields a wider distribution of scoring between 0 and 1, accurately ranking candidates.
