# Free-Text Complaint Retrieval Pipeline

## Prinsip
Keluhan bebas (free-text) dari user diproses melalui pipeline normalisasi → ekspansi → retrieval. Tidak hanya bergantung pada tombol frontend.

## Pipeline

```
ComplaintInput (free text)
  → extract_recommendation_terms() — split "dan"/"dengan"/"," → primary_terms
  → expand_symptoms() — lookup SYMPTOM_ALIASES → expanded_terms
  → recommend_herbs_light_v3() — query V3 (Symptom + SymptomAlias match)
  → fulltext fallback (jika V3 kosong dan index ada)
  → legacy_v2 fallback (TherapeuticUse match)
  → response builder
```

## Alias Mapping (symptom_aliases.py)

Keluhan umum Indonesia yang didukung:

| Keluhan | Alias |
|---------|-------|
| panas dalam | tenggorokan panas, mulut terasa panas, iritasi tenggorokan, radang mulut, sariawan |
| sariawan | luka mulut, stomatitis, ulkus mulut, radang mulut |
| batuk berdahak | batuk, dahak, ekspektoran, mukolitik |
| tenggorokan gatal | iritasi tenggorokan, radang tenggorokan |
| demam | badan panas, suhu tinggi, antipiretik |
| maag | sakit lambung, asam lambung, perut perih |
| diare | mencret, buang air besar cair |
| sakit kepala | pusing, migrain, sefalgia |
| masuk angin | flu, pilek, badan pegal, kembung |
| sakit gigi | nyeri gigi, gigi berlubang, radang gusi |
| insomnia | susah tidur, gangguan tidur, sedatif |
| radang tenggorokan | sakit tenggorokan, faringitis |
| luka | luka bakar, antiseptik, penyembuhan luka |
| tekanan darah tinggi | hipertensi, darah tinggi |
| diabetes | gula darah tinggi, kencing manis |

## Neo4j Seed Data (106)

Cypher `106_seed_common_indonesian_complaint_aliases.cypher` menambahkan:
- Symptom nodes: sariawan, panas dalam, demam, maag, diare
- SymptomAlias nodes: luka mulut, stomatitis, tenggorokan panas, dll.
- MAY_HELP_WITH relationships (hanya jika herb sudah ada di graph)

## Jika Hasil Kosong

Backend mengembalikan:
```json
{
  "status": "completed",
  "recommendations": [],
  "warnings": ["Belum ditemukan kandidat herbal yang cukup relevan..."],
  "suggested_terms": ["sariawan", "luka mulut", "iritasi tenggorokan"],
  "limitations": ["Keluhan awam mungkin perlu dipetakan..."]
}
```

Frontend menampilkan guided empty state, bukan halaman kosong.
