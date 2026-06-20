# Herbal Recommendation Safety Status & Scoring Fix Audit

## Cause of Issues
1. **safety_status UnknownPropertyKeyWarning**: The Neo4j Cypher query checked `h.safety_status` directly. When new nodes or nodes without this property were loaded, Neo4j triggered a warning.
2. **Flat/low score values**: The orchestrator recalculated candidate score using list-overlap on client side instead of passing granular Cypher score metrics which compute alias quality, compound count scaling, and safety status.

## Changes Applied
- Safe safety status lookup in query templates (coalescing to unknown, checking relationship presence first).
- Scoring v2 formulation utilizing Cypher returned scores directly.
- Added helpers to format safety labels and candidate quality strings.
