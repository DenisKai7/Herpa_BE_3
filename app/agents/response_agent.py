from app.agents.state import AgentState


class ResponseAgent:
    async def run(self, state: AgentState) -> AgentState:
        state["grounded_answer"] = state.get("draft_answer")
        return state
