from app.agents.state import AgentState
from app.graph.grounding_validator import validate_grounding


class GroundingValidatorAgent:
    async def run(self, state: AgentState) -> AgentState:
        result = validate_grounding(
            state.get("draft_answer") or "",
            state.get("retrieval", {}),
            state.get("citations", []),
            attachments=state.get("attachment_context"),
        )
        state["grounding_status"] = result["status"]
        state["confidence"] = result["confidence"]
        state["warnings"] = result["warnings"]
        return state
