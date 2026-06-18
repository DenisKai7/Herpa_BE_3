// Non-destructive performance indexes for actual HERPA Neo4j schema.
// Run manually after reviewing target database using 'SHOW FULLTEXT INDEXES'.

CREATE FULLTEXT INDEX herb_fulltext_idx IF NOT EXISTS
FOR (h:Herb)
ON EACH [
    h.commonName,
    h.canonicalScientificName,
    h.latinName,
    h.localNames
];

CREATE INDEX herb_id_idx IF NOT EXISTS
FOR (h:Herb)
ON (h.id);

CREATE INDEX compound_name_idx IF NOT EXISTS
FOR (c:Compound)
ON (c.name);

CREATE INDEX therapeutic_use_name_idx IF NOT EXISTS
FOR (u:TherapeuticUse)
ON (u.name);

SHOW FULLTEXT INDEXES
YIELD
    name,
    state,
    populationPercent,
    labelsOrTypes,
    properties
WHERE name = 'herb_fulltext_idx'
RETURN
    name,
    state,
    populationPercent,
    labelsOrTypes,
    properties;
