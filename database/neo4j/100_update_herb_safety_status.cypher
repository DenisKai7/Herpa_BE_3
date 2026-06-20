// HERPA - Update Herb safety_status from existing safety relationships.
// Safe to rerun. Non-destructive.

MATCH (h:Herb)
OPTIONAL MATCH (h)-[:HAS_CONTRAINDICATION]->(contra:Contraindication)
OPTIONAL MATCH (h)-[:HAS_INTERACTION]->(interaction:DrugInteraction)
OPTIONAL MATCH (h)-[:HAS_WARNING]->(warning:SafetyWarning)
OPTIONAL MATCH (h)-[:HAS_TOXICITY]->(tox:ToxicityCategory)
WITH
  h,
  count(DISTINCT contra) AS contraindication_count,
  count(DISTINCT interaction) AS interaction_count,
  count(DISTINCT warning) AS warning_count,
  count(DISTINCT tox) AS toxicity_count
SET
  h.safety_status =
    CASE
      WHEN contraindication_count > 0 THEN "caution"
      WHEN interaction_count > 0 THEN "caution"
      WHEN warning_count > 0 THEN "caution"
      WHEN toxicity_count > 0 THEN "caution"
      ELSE "unknown"
    END,
  h.safety_status_reason =
    CASE
      WHEN contraindication_count > 0 THEN "Memiliki data kontraindikasi pada knowledge graph."
      WHEN interaction_count > 0 THEN "Memiliki data interaksi obat pada knowledge graph."
      WHEN warning_count > 0 THEN "Memiliki data peringatan penggunaan pada knowledge graph."
      WHEN toxicity_count > 0 THEN "Memiliki data toksisitas pada knowledge graph."
      ELSE "Data keamanan spesifik belum cukup pada knowledge graph."
    END,
  h.safety_status_updated_at = datetime()
RETURN
  h.safety_status AS safety_status,
  count(h) AS total
ORDER BY total DESC;
