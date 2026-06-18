from app.agents.state import AgentState


class RecommendationAgent:
    async def run(self, state: AgentState) -> AgentState:
        if state.get("intent") == "recommendation":
            state.setdefault("specialist_guidance", []).append(
                "Rekomendasi hanya boleh menjelaskan kandidat yang telah lolos retrieval dan safety validation."
            )
        return state
