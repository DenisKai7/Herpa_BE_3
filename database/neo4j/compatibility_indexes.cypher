// Optional non-destructive indexes for actual HERPA Neo4j schema.
// Run manually only after reviewing target database.

CREATE INDEX herb_common_name_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.commonName);

CREATE INDEX herb_scientific_name_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.canonicalScientificName);

CREATE INDEX herb_latin_name_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.latinName);

CREATE INDEX herb_id_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.id);
