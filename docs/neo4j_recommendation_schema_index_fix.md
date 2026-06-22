# Neo4j Recommendation Schema & Index Fix

## File Migration

### 104 — Normalized Properties
File: `database/neo4j/104_fix_normalized_properties_for_recommendation.cypher`

Memperbaiki normalisasi `name_lc` property pada node:
- `Symptom.name_lc`
- `SymptomAlias.name_lc`
- `Herb.commonName_lc`, `canonicalScientificName_lc`, `latinName_lc`
- `TherapeuticUse.name_lc`
- `TraditionalUse.title_lc`, `description_lc`, `category_lc`

Menggunakan `coalesce(field, "")` untuk menghindari null → error.

### 105 — Fulltext Indexes
File: `database/neo4j/105_fix_recommendation_fulltext_indexes.cypher`

Membuat indexes:
- `symptom_name_lc_idx` — Symptom.name_lc
- `symptom_alias_name_lc_idx` — SymptomAlias.name_lc
- `therapeutic_use_name_lc_idx` — TherapeuticUse.name_lc
- `traditional_use_title_lc_idx` — TraditionalUse.title_lc
- `traditional_use_category_lc_idx` — TraditionalUse.category_lc
- `symptom_alias_fulltext_idx` — fulltext: Symptom|SymptomAlias [name, name_lc]
- `herbal_use_fulltext_idx` — fulltext: TraditionalUse|TherapeuticUse [title, description, category, name, *_lc]

### 106 — Complaint Aliases Seed
File: `database/neo4j/106_seed_common_indonesian_complaint_aliases.cypher`

Menambahkan Symptom + SymptomAlias nodes untuk keluhan umum Indonesia.

## Urutan Eksekusi

```
1. Jalankan 104 (normalisasi properties)
2. Jalankan 105 (buat indexes)
3. Jalankan 106 (seed alias keluhan)
```

## Fulltext Index Guard

Backend memeriksa keberadaan fulltext index sebelum query:

```python
ft_status = await self.fulltext_index_status("symptom_alias_fulltext_idx")
if ft_status.get("exists") and ft_status.get("state") == "ONLINE":
    # use fulltext query
else:
    # skip, log warning — not a 500 error
```

## Query yang Diperbarui

### HERBAL_RECOMMENDATION_LIGHT_LEGACY
- **Sebelum**: `any(useName IN collect(DISTINCT u.name) WHERE ...)` → aggregate error
- **Sesudah**: `WITH collect() AS matched_use_lc` → `size([term IN $primary_terms WHERE term IN matched_use_lc])`
- Menerima `$primary_terms` dan `$expanded_terms` (bukan `$terms`)

### HERBAL_RECOMMENDATION_LIGHT_V3
- **Sebelum**: Hanya `s.name_lc IN $expanded_terms`
- **Sesudah**: Juga match via `EXISTS { MATCH (s)-[:HAS_ALIAS]->(a) WHERE a.name_lc IN $expanded_terms }`
