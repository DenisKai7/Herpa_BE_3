CREATE FULLTEXT INDEX plant_search IF NOT EXISTS FOR (n:Plant) ON EACH [n.local_name,n.indonesian_name,n.scientific_name,n.synonyms];
CREATE FULLTEXT INDEX compound_search IF NOT EXISTS FOR (n:Compound) ON EACH [n.name,n.synonyms,n.molecular_formula];
CREATE FULLTEXT INDEX symptom_search IF NOT EXISTS FOR (n:Symptom) ON EACH [n.name,n.synonyms];
CREATE INDEX evidence_level_idx IF NOT EXISTS FOR (n:Evidence) ON (n.level);
CREATE INDEX publication_pmid_idx IF NOT EXISTS FOR (n:Publication) ON (n.pubmed_id);
