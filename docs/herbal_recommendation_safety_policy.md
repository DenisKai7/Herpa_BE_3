# Herbal Recommendation Safety Policy

## Principle
HERPA recommendation is educational, not diagnosis and not a substitute for healthcare professional examination.

## Safety status mapping

- `safe`: sufficient positive safety information.
- `caution`: toxicity, contraindication, or interaction data exists but is not a hard stop.
- `unsafe`: strong contraindication, serious interaction, strong toxicity, or user red flag conflict.
- `unknown`: no specific safety data in the knowledge graph.

## Empty safety data
Empty safety data must not become `unsafe`. It maps to:

```json
{
  "safety_status": "unknown",
  "safety_label": "Data keamanan belum cukup"
}
```

## Evidence status

- no source → `unavailable` / `Data bukti belum tersedia`
- one source → `limited` / `Data bukti terbatas`
- two or more sources → `available` / `Data pendukung tersedia`

## Red flag cough advice
For cough/throat complaints, UI should show advice to seek care if symptoms include shortness of breath, high fever, chest pain, bloody sputum, or persist beyond 3 days.

## Dose policy
Do not provide clinical dosage unless validated source data exists. Use product-label/farmacist consultation wording when dose is absent.
