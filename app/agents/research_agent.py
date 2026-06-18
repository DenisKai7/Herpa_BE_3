from app.agents.state import AgentState


class ResearchAgent:
    async def run(self, state: AgentState) -> AgentState:
        if state.get("persona") == "peneliti" or state.get("intent") == "research":
            state.setdefault("specialist_guidance", []).append(
                "Untuk riset, sertakan simplisia, ekstraksi/fraksinasi, isolasi, HPLC/GC-MS/LC-MS, desain in-vitro/in-vivo, serta tingkat bukti dan sumber."
            )
        return state
