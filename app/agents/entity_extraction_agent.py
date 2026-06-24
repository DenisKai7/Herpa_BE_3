from app.agents.state import AgentState
from app.graph.entity_resolver import resolve_entities


class EntityExtractionAgent:
    async def run(self, state: AgentState) -> AgentState:
        resolved = [entity.model_dump() for entity in resolve_entities(state.get("user_query", ""))]
        vlm_entities = [e for e in state.get("entities", []) if e.get("source") == "vlm"]
        existing_names = {e.get("canonical_name", "").lower() for e in resolved}
        merged = []
        for ve in vlm_entities:
            if ve.get("canonical_name", "").lower() not in existing_names:
                merged.append(ve)
        merged.extend(resolved)
        state["entities"] = merged
        return state
