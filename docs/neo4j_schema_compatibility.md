# Neo4j schema compatibility HERPA

Backend memakai schema Neo4j aktual Aura tanpa migrasi destruktif.

## Labels aktual
- `Herb`
- `Compound`
- `TherapeuticUse`
- `Family`
- `ProteinTarget`
- `ToxicityCategory`
- `Source`

## Relationship aktual
- `HAS_COMPOUND`
- `USED_FOR`
- `BELONGS_TO`
- `HAS_PROTEIN_TARGET`
- `HAS_TOXICITY`
- `VERIFIED_BY`
- `HAS_COMPOUND_CLASS`
- `TARGETS_PROTEIN`

## Canonical output backend
Database internal tetap dipetakan ke output lama agar frontend/agent tetap stabil:

```python
plant = {
    "plant_id": h.id,
    "local_name": h.commonName,
    "scientific_name": coalesce(h.canonicalScientificName, h.latinName),
    "latin_name": h.latinName,
    "synonyms": h.localNames,
    "simplisia_name": h.simplisiaName,
}
```

## Query utama
- `HERB_BY_NAME`: search `commonName`, `canonicalScientificName`, `latinName`, array `localNames`.
- `HERBS_BY_THERAPEUTIC_USE`: search `TherapeuticUse.name` via `USED_FOR`.
- `HERBS_BY_COMPOUND`: search `Compound.name` via `HAS_COMPOUND`.
- `HERB_PROTEIN_TARGETS`: `HAS_PROTEIN_TARGET`.
- `HERB_TOXICITY`: `HAS_TOXICITY`.
- `HERB_SOURCES`: `VERIFIED_BY`.

## Error semantics
- Empty result => `grounding_status=insufficient`, warning data belum ditemukan.
- Neo4j connection/session/cypher error => `NEO4J_UNAVAILABLE`.

## Runtime validation
```powershell
python .\scripts\test_neo4j_schema.py
```

## Optional integration test
```powershell
$env:RUN_NEO4J_INTEGRATION_TESTS="true"
pytest tests/integration/test_neo4j_actual_schema.py -q
```
