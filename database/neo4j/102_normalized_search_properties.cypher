// Safe to rerun. Non-destructive.

MATCH (s:Symptom)
SET s.name_lc = toLower(s.name);

MATCH (a:SymptomAlias)
SET a.name_lc = toLower(a.name);

MATCH (h:Herb)
SET
  h.commonName_lc = toLower(h.commonName),
  h.canonicalScientificName_lc = toLower(h.canonicalScientificName),
  h.latinName_lc = toLower(h.latinName);

MATCH (u:TherapeuticUse)
SET u.name_lc = toLower(u.name);

MATCH (tu:TraditionalUse)
SET
  tu.title_lc = toLower(tu.title),
  tu.description_lc = toLower(tu.description),
  tu.category_lc = toLower(tu.category);

RETURN "normalized search properties updated" AS status;
