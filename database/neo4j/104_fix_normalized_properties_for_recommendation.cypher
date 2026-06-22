// HERPA recommendation normalized search properties.
// Extends 102 with coalesce() safety and TraditionalUse normalization.
// Safe to rerun. Non-destructive.

MATCH (s:Symptom)
SET s.name_lc = toLower(coalesce(s.name, ""));

MATCH (a:SymptomAlias)
SET a.name_lc = toLower(coalesce(a.name, ""));

MATCH (h:Herb)
SET
  h.commonName_lc = toLower(coalesce(h.commonName, "")),
  h.canonicalScientificName_lc = toLower(coalesce(h.canonicalScientificName, "")),
  h.latinName_lc = toLower(coalesce(h.latinName, ""));

MATCH (u:TherapeuticUse)
SET u.name_lc = toLower(coalesce(u.name, ""));

MATCH (tu:TraditionalUse)
SET
  tu.title_lc = toLower(coalesce(tu.title, "")),
  tu.description_lc = toLower(coalesce(tu.description, "")),
  tu.category_lc = toLower(coalesce(tu.category, ""));

RETURN "normalized properties fixed" AS status;
