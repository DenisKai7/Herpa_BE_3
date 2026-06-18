from app.agents.state import AgentState


class BotanicalAgent:
    async def run(self, state: AgentState) -> AgentState:
        guidance = state.setdefault("specialist_guidance", [])
        if any(entity.get("entity_type") == "plant" for entity in state.get("entities", [])):
            guidance.append(
                "Bahas nama ilmiah canonical, famili, sinonim, bagian tanaman, dan simplisia bila datanya tersedia."
            )
        return state
