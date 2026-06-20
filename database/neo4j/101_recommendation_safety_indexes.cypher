CREATE INDEX herb_safety_status_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.safety_status);

CREATE INDEX herb_id_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.id);

CREATE INDEX symptom_name_idx IF NOT EXISTS
FOR (s:Symptom)
ON (s.name);

CREATE INDEX symptom_alias_name_idx IF NOT EXISTS
FOR (a:SymptomAlias)
ON (a.name);
