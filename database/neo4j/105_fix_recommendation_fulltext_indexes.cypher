// HERPA recommendation fulltext indexes for free-text complaint support.
// Extends 103 with additional indexes.
// Safe to rerun. Non-destructive.

CREATE INDEX symptom_name_lc_idx IF NOT EXISTS
FOR (s:Symptom)
ON (s.name_lc);

CREATE INDEX symptom_alias_name_lc_idx IF NOT EXISTS
FOR (a:SymptomAlias)
ON (a.name_lc);

CREATE INDEX therapeutic_use_name_lc_idx IF NOT EXISTS
FOR (u:TherapeuticUse)
ON (u.name_lc);

CREATE INDEX traditional_use_title_lc_idx IF NOT EXISTS
FOR (tu:TraditionalUse)
ON (tu.title_lc);

CREATE INDEX traditional_use_category_lc_idx IF NOT EXISTS
FOR (tu:TraditionalUse)
ON (tu.category_lc);

CREATE FULLTEXT INDEX symptom_alias_fulltext_idx IF NOT EXISTS
FOR (n:Symptom|SymptomAlias)
ON EACH [n.name, n.name_lc];

CREATE FULLTEXT INDEX herbal_use_fulltext_idx IF NOT EXISTS
FOR (n:TraditionalUse|TherapeuticUse)
ON EACH [n.title, n.description, n.category, n.name, n.title_lc, n.description_lc, n.category_lc, n.name_lc];
