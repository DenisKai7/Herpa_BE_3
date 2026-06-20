MATCH (n)
RETURN labels(n) AS labels, count(n) AS total
ORDER BY total DESC;

MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(r) AS total
ORDER BY total DESC;

MATCH (h:Herb)
RETURN count(h) AS total_herbs;

MATCH (n:TraditionalUse)
RETURN count(n) AS total_traditional_uses;

MATCH (n:PreparationMethod)
RETURN count(n) AS total_preparation_methods;

MATCH (n:UsageGuideline)
RETURN count(n) AS total_usage_guidelines;

MATCH (n:SafetyWarning)
RETURN count(n) AS total_safety_warnings;

MATCH (n:Claim)
RETURN count(n) AS total_claims;

MATCH (n:Evidence)
RETURN count(n) AS total_evidence;

MATCH (n:Symptom)
RETURN count(n) AS total_symptoms;

MATCH (n:SymptomAlias)
RETURN count(n) AS total_symptom_aliases;

MATCH (n:PopulationRisk)
RETURN count(n) AS total_population_risks;

MATCH (n:Audience)
RETURN collect(n.id) AS audiences;
