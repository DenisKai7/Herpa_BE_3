CREATE CONSTRAINT plant_id_unique IF NOT EXISTS FOR (n:Plant) REQUIRE n.plant_id IS UNIQUE;
CREATE CONSTRAINT compound_id_unique IF NOT EXISTS FOR (n:Compound) REQUIRE n.compound_id IS UNIQUE;
CREATE CONSTRAINT symptom_id_unique IF NOT EXISTS FOR (n:Symptom) REQUIRE n.symptom_id IS UNIQUE;
CREATE CONSTRAINT evidence_id_unique IF NOT EXISTS FOR (n:Evidence) REQUIRE n.evidence_id IS UNIQUE;
CREATE CONSTRAINT publication_id_unique IF NOT EXISTS FOR (n:Publication) REQUIRE n.source_id IS UNIQUE;
CREATE CONSTRAINT drug_id_unique IF NOT EXISTS FOR (n:Drug) REQUIRE n.drug_id IS UNIQUE;
CREATE CONSTRAINT icd10_code_unique IF NOT EXISTS FOR (n:ICD10) REQUIRE n.icd10_code IS UNIQUE;
CREATE CONSTRAINT quiz_concept_id_unique IF NOT EXISTS FOR (n:QuizConcept) REQUIRE n.concept_id IS UNIQUE;
