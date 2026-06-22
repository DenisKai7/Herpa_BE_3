// Common Indonesian complaint aliases for recommendation.
// Safe to rerun. Non-destructive.

MERGE (s1:Symptom {id: "SYM-SARIAWAN"})
SET
  s1.name = "sariawan",
  s1.name_lc = "sariawan",
  s1.category = "mulut dan tenggorokan";

MERGE (a11:SymptomAlias {name: "luka mulut"})
SET a11.name_lc = "luka mulut";
MERGE (a12:SymptomAlias {name: "stomatitis"})
SET a12.name_lc = "stomatitis";
MERGE (a13:SymptomAlias {name: "ulkus mulut"})
SET a13.name_lc = "ulkus mulut";
MERGE (s1)-[:HAS_ALIAS]->(a11);
MERGE (s1)-[:HAS_ALIAS]->(a12);
MERGE (s1)-[:HAS_ALIAS]->(a13);

MERGE (s2:Symptom {id: "SYM-PANAS-DALAM"})
SET
  s2.name = "panas dalam",
  s2.name_lc = "panas dalam",
  s2.category = "keluhan umum tradisional";

MERGE (a21:SymptomAlias {name: "tenggorokan panas"})
SET a21.name_lc = "tenggorokan panas";
MERGE (a22:SymptomAlias {name: "mulut terasa panas"})
SET a22.name_lc = "mulut terasa panas";
MERGE (a23:SymptomAlias {name: "iritasi tenggorokan"})
SET a23.name_lc = "iritasi tenggorokan";
MERGE (a24:SymptomAlias {name: "radang mulut"})
SET a24.name_lc = "radang mulut";
MERGE (s2)-[:HAS_ALIAS]->(a21);
MERGE (s2)-[:HAS_ALIAS]->(a22);
MERGE (s2)-[:HAS_ALIAS]->(a23);
MERGE (s2)-[:HAS_ALIAS]->(a24);

MERGE (s3:Symptom {id: "SYM-DEMAM"})
SET
  s3.name = "demam",
  s3.name_lc = "demam",
  s3.category = "keluhan umum";

MERGE (a31:SymptomAlias {name: "badan panas"})
SET a31.name_lc = "badan panas";
MERGE (a32:SymptomAlias {name: "suhu tinggi"})
SET a32.name_lc = "suhu tinggi";
MERGE (s3)-[:HAS_ALIAS]->(a31);
MERGE (s3)-[:HAS_ALIAS]->(a32);

MERGE (s4:Symptom {id: "SYM-MAAG"})
SET
  s4.name = "maag",
  s4.name_lc = "maag",
  s4.category = "pencernaan";

MERGE (a41:SymptomAlias {name: "sakit lambung"})
SET a41.name_lc = "sakit lambung";
MERGE (a42:SymptomAlias {name: "asam lambung"})
SET a42.name_lc = "asam lambung";
MERGE (a43:SymptomAlias {name: "perut perih"})
SET a43.name_lc = "perut perih";
MERGE (s4)-[:HAS_ALIAS]->(a41);
MERGE (s4)-[:HAS_ALIAS]->(a42);
MERGE (s4)-[:HAS_ALIAS]->(a43);

MERGE (s5:Symptom {id: "SYM-DIARE"})
SET
  s5.name = "diare",
  s5.name_lc = "diare",
  s5.category = "pencernaan";

MERGE (a51:SymptomAlias {name: "mencret"})
SET a51.name_lc = "mencret";
MERGE (a52:SymptomAlias {name: "buang air besar cair"})
SET a52.name_lc = "buang air besar cair";
MERGE (s5)-[:HAS_ALIAS]->(a51);
MERGE (s5)-[:HAS_ALIAS]->(a52);

// Connect known likely herbal candidates only if they already exist.
// Keep wording safe and evidence-aware.

MATCH (h:Herb)
WHERE toLower(coalesce(h.commonName, "")) IN [
  "daun sirih",
  "sirih",
  "sirih merah",
  "kunyit",
  "temulawak",
  "lidah buaya",
  "madu",
  "jeruk nipis"
]
MERGE (h)-[:MAY_HELP_WITH]->(s1)
MERGE (h)-[:MAY_HELP_WITH]->(s2);

RETURN "common complaint aliases seeded" AS status;
