from pathlib import Path


def main() -> None:
    print("Supabase seed:", Path("database/supabase/seed.sql").resolve())
    print("Neo4j seed:", Path("database/neo4j/seed.cypher").resolve())
    print("Dataset ingestion: python -m data_pipeline.ingest_neo4j")


if __name__ == "__main__":
    main()
