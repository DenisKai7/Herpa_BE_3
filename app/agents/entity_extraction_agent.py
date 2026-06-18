from app.agents.state import AgentState
from app.graph.entity_resolver import resolve_entities


class EntityExtractionAgent:
    async def run(self, state: AgentState) -> AgentState:
        state["entities"] = [entity.model_dump() for entity in resolve_entities(state.get("user_query", ""))]
        return state
