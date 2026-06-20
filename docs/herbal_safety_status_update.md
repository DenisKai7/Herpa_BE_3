# IDEMPOTENT SAFETY STATUS UPDATE

Run this script in Neo4j Browser to update `safety_status` on all `Herb` nodes based on safety relationships:
`database/neo4j/100_update_herb_safety_status.cypher`

This prevents reliance on pre-existing property values.
Query fallback parses relationships directly to assign status caution/safe.
Unknown safety status maps to `"Data keamanan belum cukup"`, avoiding false negative warnings.
