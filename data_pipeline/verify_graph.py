import asyncio, os
from neo4j import AsyncGraphDatabase


async def main() -> None:
    d = AsyncGraphDatabase.driver(
        os.environ["NEO4J_URI"], auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    )
    async with d.session(database=os.getenv("NEO4J_DATABASE", "neo4j")) as s:
        row = await (await s.run("MATCH (p:Plant) RETURN count(p) AS plants")).single()
        print(dict(row or {}))
    await d.close()


if __name__ == "__main__":
    asyncio.run(main())
