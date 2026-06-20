# Neo4j Enrichment v2 Schema

Read-only validation: `database/neo4j/validate_enrichment_v2.cypher`.

Labels expected: `Herb`, `Compound`, `TherapeuticUse`, `Family`, `ProteinTarget`, `ToxicityCategory`, `Source`, plus enrichment labels `TraditionalUse`, `PreparationMethod`, `UsageGuideline`, `SafetyWarning`, `PlantPart`, `StorageGuideline`, `MythFact`, `QualityStandard`, `ClinicalGuideline`, `DrugInteraction`, `Contraindication`, `PharmacokineticProfile`, `ResearchTopic`, `Claim`, `Evidence`, `Symptom`, `SymptomAlias`, `PopulationRisk`, `Audience`, `Formulation`, `EducationModule`, `PhytochemicalScreening`.

Core enrichment path: `(:Herb)-[:MAY_HELP_WITH]->(:Symptom)` and `(:Symptom)-[:HAS_ALIAS]->(:SymptomAlias)` power recommendation search. Detail tabs read `HAS_TRADITIONAL_USE`, `HAS_PREPARATION`, `HAS_USAGE_GUIDELINE`, `HAS_WARNING`, `USES_PART`, `HAS_STORAGE_GUIDELINE`, `HAS_MYTH_FACT`, `HAS_QUALITY_STANDARD`, `HAS_CLINICAL_GUIDELINE`, `HAS_INTERACTION`, `HAS_CONTRAINDICATION`, `HAS_PHARMACOKINETIC_PROFILE`, `HAS_RESEARCH_TOPIC`, `HAS_CLAIM`, `SUPPORTED_BY`, `FROM_SOURCE`.

No destructive DB ops needed.
