# NEO4J SCHEMA FIX IMPLEMENTATION REPORT

## Penyebab error awal
Backend terkoneksi ke Neo4j, tetapi query repository memakai schema lama: `Plant`, `PlantPart`, `TraditionalUse`, `CONTAINS_COMPOUND`, `HAS_TRADITIONAL_USE`, dst. Database aktual memakai `Herb`, `TherapeuticUse`, `HAS_COMPOUND`, `USED_FOR`, dst. Schema mismatch menyebabkan query gagal/hasil kosong dan muncul sebagai `NEO4J_UNAVAILABLE`.

## Schema lama yang salah
- Labels: `Plant`, `PlantPart`, `TraditionalUse`, `Contraindication`, `SideEffect`.
- Props: `local_name`, `scientific_name`, `synonyms`.
- Rels: `CONTAINS_COMPOUND`, `HAS_TRADITIONAL_USE`, `HAS_PART`, `HAS_CONTRAINDICATION`, `HAS_SIDE_EFFECT`.

## Schema aktual
- Labels: `Herb`, `Compound`, `TherapeuticUse`, `Family`, `ProteinTarget`, `ToxicityCategory`, `Source`.
- Rels: `HAS_COMPOUND`, `USED_FOR`, `BELONGS_TO`, `HAS_PROTEIN_TARGET`, `HAS_TOXICITY`, `VERIFIED_BY`, `HAS_COMPOUND_CLASS`, `TARGETS_PROTEIN`.

## File diubah
- `app/graph/query_templates.py`
- `app/graph/repositories.py`
- `app/graph/entity_resolver.py`
- `app/graph/retriever.py`
- `app/graph/context_builder.py`
- `app/graph/neo4j_client.py`
- `app/agents/retrieval_planner_agent.py`
- `app/core/logging.py`

## File dibuat
- `app/graph/schema_mapping.py`
- `docs/neo4j_schema_compatibility.md`
- `docs/neo4j_schema_compatibility_audit.md`
- `NEO4J_SCHEMA_FIX_IMPLEMENTATION_REPORT.md`
- `scripts/test_neo4j_schema.py`
- `tests/unit/test_neo4j_schema_mapping.py`
- `tests/integration/test_neo4j_actual_schema.py`
- `database/neo4j/compatibility_indexes.cypher`

## Query diperbaiki
- `HERB_BY_NAME`
- `PLANT_BY_NAME = HERB_BY_NAME` alias kompatibilitas
- `HERBS_BY_THERAPEUTIC_USE`
- `HERBS_BY_COMPOUND`
- `HERB_PROTEIN_TARGETS`
- `HERB_TOXICITY`
- `HERB_SOURCES`
- `COMPOUND_BY_NAME` memakai `Herb`/`HAS_COMPOUND`

## Canonical mapping
- `Herb.commonName` -> `plant.local_name`
- `Herb.canonicalScientificName`/`latinName` -> `plant.scientific_name`
- `Herb.localNames` -> `plant.synonyms`
- `HAS_COMPOUND` -> `compounds`
- `USED_FOR` -> `therapeutic_uses` + compatibility `traditional_uses`
- `BELONGS_TO` -> `families`
- `HAS_PROTEIN_TARGET` -> `protein_targets`
- `HAS_TOXICITY` -> `toxicity`
- `VERIFIED_BY` -> `sources`

## Runtime Neo4j result
- Health: `True`
- Herb nodes: `594`
- HAS_COMPOUND relationships: `2846`
- `plant_by_name("kunyit")`: `3` rows, first `HRB-001-KUN`, compounds `8`, uses `12`
- `plant_by_name("jahe")`: `3` rows, first `HRB-002-JAH`, compounds `9`, uses `9`

## Validasi
- `python -m compileall app`: PASS
- `ruff check .`: PASS
- `mypy app`: PASS
- `pytest -q`: PASS (`45 passed, 1 skipped`)
- `ruff format --check .`: PASS (`160 files already formatted`)
- `python .\scripts\test_neo4j_schema.py`: PASS

## Catatan
- Tidak ada query write/destructive dijalankan.
- File index opsional dibuat, tidak dijalankan otomatis.
- Chat endpoint tidak dites end-to-end dengan token Supabase user nyata di sesi ini; repository GraphRAG dependency sudah tervalidasi langsung ke Aura.
