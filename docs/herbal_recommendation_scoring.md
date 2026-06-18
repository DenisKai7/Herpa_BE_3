# Herbal Recommendation Scoring

## Score safety
All numeric score fields must be finite `0.0–1.0`. Invalid values (`NaN`, `Infinity`, non-number, `None`) are clamped via `clamp_score()`.

## Formula

```text
confidence =
  symptom_match_score * 0.40
  + alias_match_score * 0.20
  + compound_score * 0.15
  + evidence_score * 0.15
  + safety_score * 0.10
```

## Sub-scores

- `symptom_match_score`: direct matched symptom ratio.
- `alias_match_score`: matched expanded alias ratio.
- `compound_score`: `1.0` when active compounds are available, otherwise `0.0`.
- `evidence_score`: `min(source_count / 3, 1.0)`.
- `safety_score`:
  - `unknown`: `0.5`
  - `safe`: `0.8`
  - `caution`: `0.4`
  - `unsafe`: `0.0`

## Relevance labels

- `>= 0.75`: `high` / `Relevansi tinggi`
- `>= 0.50`: `medium` / `Relevansi sedang`
- `> 0`: `low` / `Relevansi rendah`
- `0`: `unknown` / `Relevansi belum tersedia`

## Threshold

- `< 0.20`: excluded as `confidence terlalu rendah`, unless no displayable candidate exists.
- `< 0.50`: displayed as low-confidence candidate awal.
