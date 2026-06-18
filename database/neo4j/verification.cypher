MATCH (p:Plant) RETURN count(p) AS plants;
MATCH (p:Plant)-[:CONTAINS_COMPOUND]->(c:Compound) RETURN p.local_name,c.name LIMIT 20;
MATCH (p:Plant)-[:MAY_RELIEVE]->(s:Symptom) RETURN p.local_name,s.name LIMIT 20;
