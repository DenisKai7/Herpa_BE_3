CREATE INDEX herb_id_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.id);

CREATE INDEX herb_common_name_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.commonName);

CREATE INDEX herb_canonical_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.canonicalScientificName);

CREATE INDEX symptom_name_idx IF NOT EXISTS
FOR (s:Symptom)
ON (s.name);

CREATE INDEX symptom_alias_name_idx IF NOT EXISTS
FOR (a:SymptomAlias)
ON (a.name);

CREATE INDEX traditional_use_category_idx IF NOT EXISTS
FOR (n:TraditionalUse)
ON (n.category);

CREATE FULLTEXT INDEX herb_usage_fulltext_idx IF NOT EXISTS
FOR (n:TraditionalUse|PreparationMethod|UsageGuideline|SafetyWarning|Claim)
ON EACH [n.title, n.description, n.category, n.text];
