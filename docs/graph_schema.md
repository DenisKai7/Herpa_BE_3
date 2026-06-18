# Skema Knowledge Graph

Node inti: `Plant`, `PlantPart`, `Simplisia`, `Compound`, `CompoundClass`, `Symptom`, `Condition`, `Contraindication`, `SideEffect`, `Drug`, `Evidence`, `Publication`, `Study`, `MolecularTarget`, `Mechanism`, `ADMEProperty`, `ICD10`, dan `QuizConcept`.

Relasi inti: `HAS_PART`, `CONTAINS_COMPOUND`, `MAY_RELIEVE`, `HAS_CONTRAINDICATION`, `HAS_SIDE_EFFECT`, `INTERACTS_WITH`, `HAS_MECHANISM`, `ACTS_ON`, `SUPPORTED_BY`, `REPORTED_IN`, dan `HAS_ADME`.

Semua query aplikasi berasal dari allowlist `app/graph/query_templates.py`; user dan model tidak dapat mengirim Cypher mentah.
