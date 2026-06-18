# Audit kompatibilitas schema Neo4j aktual

## Masalah awal
Backend konek ke Aura, tetapi retrieval memakai schema lama/hipotetis. Akibatnya query gagal/hasil kosong salah diklasifikasi menjadi `NEO4J_UNAVAILABLE`.

## Referensi schema lama ditemukan
- `app/graph/query_templates.py`
  - `:Plant`, `:PlantPart`, `TraditionalUse`, `Contraindication`, `SideEffect`
  - `local_name`, `scientific_name`, `synonyms`
  - `CONTAINS_COMPOUND`, `HAS_TRADITIONAL_USE`, `HAS_PART`, `HAS_CONTRAINDICATION`, `HAS_SIDE_EFFECT`
  - `Symptom`, `MAY_RELIEVE`, `Drug`, `Evidence`, `HAS_ACTIVITY`, `ACTS_ON`, `MolecularTarget`
- `app/graph/repositories.py`
  - Mengimpor `PLANT_BY_NAME`, `PLANTS_FOR_SYMPTOMS`, `COMPOUND_BY_NAME` lama.
- `app/graph/retriever.py`
  - Masih memakai tipe entity `plant` dan method `plant_by_name`; output canonical masih bisa dipertahankan.
- `app/graph/context_builder.py`
  - Dump JSON mentah; belum memformat `therapeutic_uses`, `protein_targets`, `toxicity`, `sources`.
- `app/logic/recommendation_orchestrator.py`
  - Output canonical frontend memakai `local_name`, `scientific_name`; ini tetap dipertahankan.
- `app/agents/graph.py`
  - Source title pakai canonical `scientific_name`; tetap kompatibel.

## Schema aktual target
- Label: `Herb`, `Compound`, `TherapeuticUse`, `Family`, `ProteinTarget`, `ToxicityCategory`, `Source`.
- Relasi: `HAS_COMPOUND`, `USED_FOR`, `BELONGS_TO`, `HAS_PROTEIN_TARGET`, `HAS_TOXICITY`, `VERIFIED_BY`, `HAS_COMPOUND_CLASS`, `TARGETS_PROTEIN`.
- Property Herb: `id`, `commonName`, `canonicalScientificName`, `latinName`, `localNames`, `simplisiaName`, `macroscopicDesc`, `microscopicDesc`, `status`, `speciesNumber`, `lastUpdated`.

## Keputusan
- Tidak mengubah DB.
- Tidak seed demo.
- Query memakai schema aktual.
- Repository tetap mengeluarkan canonical backend: `plant.local_name`, `plant.scientific_name`, `plant.synonyms`, dst.
- Hasil kosong bukan `NEO4J_UNAVAILABLE`.
