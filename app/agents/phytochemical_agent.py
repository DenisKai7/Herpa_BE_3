from app.agents.state import AgentState


class PhytochemicalAgent:
    async def run(self, state: AgentState) -> AgentState:
        guidance = state.setdefault("specialist_guidance", [])
        if state.get("persona") in {"pelajar", "peneliti", "tenaga_medis"}:
            guidance.append(
                "Pisahkan kandungan senyawa, kelas metabolit, metode identifikasi, dan data yang belum tersedia."
            )
        return state
