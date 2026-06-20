# Herbal Recommendation Scoring V3

V3 separates primary complaint coverage from expanded alias coverage.

Formula:
- primary coverage * 0.40
- expanded coverage * 0.20
- traditional use score * 0.15
- compound score * 0.05
- safety score * 0.10
- primary coverage bonus: +0.10 for full primary match, +0.05 for half match

`score` is total relevance. `primary_coverage_score` is displayed as symptom coverage.
