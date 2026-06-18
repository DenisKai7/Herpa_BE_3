import asyncio, json, os
from pathlib import Path
from neo4j import AsyncGraphDatabase
from data_pipeline.validation.plants import PlantSeed

DATA = Path(__file__).parent / "datasets" / "plants.json"


async def main() -> None:
    uri = os.environ["NEO4J_URI"]
    user = os.environ["NEO4J_USERNAME"]
    password = os.environ["NEO4J_PASSWORD"]
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    plants = [PlantSeed.model_validate(x) for x in json.loads(DATA.read_text(encoding="utf-8"))]
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    query = """UNWIND $rows AS row MERGE (p:Plant {plant_id:row.plant_id}) SET p.local_name=row.local_name,p.scientific_name=row.scientific_name,p.family=row.family,p.evidence_level=row.evidence_level,p.updated_at=datetime() FOREACH (part IN row.parts | MERGE (pp:PlantPart {name:part}) MERGE (p)-[:HAS_PART]->(pp)) FOREACH (compound IN row.compounds | MERGE (c:Compound {compound_id:compound.compound_id}) SET c.name=compound.name,c.pubchem_cid=compound.pubchem_cid MERGE (p)-[:CONTAINS_COMPOUND]->(c)) FOREACH (symptom IN row.symptoms | MERGE (s:Symptom {name:toLower(symptom)}) ON CREATE SET s.symptom_id='symptom:'+replace(toLower(symptom),' ','_') MERGE (p)-[:MAY_RELIEVE]->(s)) RETURN count(p) AS count"""
    async with driver.session(database=db) as session:
        result = await session.run(query, rows=[p.model_dump() for p in plants])
        print(await result.single())
    await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
