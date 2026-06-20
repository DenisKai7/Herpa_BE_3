# RECOMMENDATION CARD QUALITY LABELS

UI helper maps candidate scores to categorical labels:
- `score >= 0.75` → "Kandidat utama"
- `score >= 0.50` → "Kandidat relevan"
- `score >= 0.35` → "Kandidat awal"
- `score < 0.35` → "Kandidat awal, perlu verifikasi"

Provides clear user context regarding recommendation strength.
Uses `getSafetyStatusLabel` to map unknown safety to safe neutral texts.
