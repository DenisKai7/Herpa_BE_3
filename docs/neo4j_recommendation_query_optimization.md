# Neo4j Recommendation Query Optimization

V3 exact path uses normalized properties:
- `s.name_lc IN $expanded_terms`
- no `CONTAINS` in main recommendation path

Manual scripts:
- `database/neo4j/102_normalized_search_properties.cypher`
- `database/neo4j/103_recommendation_v3_indexes.cypher`

Fulltext fallback runs only if exact path returns no rows.
