class DatabaseOrchestrator:
    """Coordinates Supabase application state and Neo4j knowledge retrieval without mixing ownership."""

    def __init__(self, supabase, neo4j):
        self.supabase = supabase
        self.neo4j = neo4j
