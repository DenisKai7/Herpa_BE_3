from app.agents.state import AgentState

QUERY_TYPES = {
    "herb_by_name",
    "plant_by_name",
    "herbs_by_therapeutic_use",
    "herbs_by_compound",
    "herb_protein_targets",
    "herb_toxicity",
    "herb_sources",
}


class RetrievalPlannerAgent:
    """Builds a safe declarative plan; it never emits raw Cypher."""

    async def run(self, state: AgentState) -> AgentState:
        plan: list[dict] = []
        for entity in state.get("entities", [])[:6]:
            entity_type = entity.get("entity_type")
            if entity_type == "plant":
                plan.append({"template": "herb_by_name", "name": entity.get("original_text"), "limit": 10})
            elif entity_type == "compound":
                plan.append(
                    {"template": "herbs_by_compound", "name": entity.get("original_text"), "limit": 10}
                )
        state["graph_queries"] = plan
        return state
