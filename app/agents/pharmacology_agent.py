from app.agents.state import AgentState


class PharmacologyAgent:
    async def run(self, state: AgentState) -> AgentState:
        guidance = state.setdefault("specialist_guidance", [])
        guidance.append(
            "Bedakan penggunaan tradisional, aktivitas farmakologis, mekanisme, bukti praklinik, dan bukti klinis."
        )
        return state
