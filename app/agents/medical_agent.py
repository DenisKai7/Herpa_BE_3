from app.agents.state import AgentState


class MedicalAgent:
    async def run(self, state: AgentState) -> AgentState:
        if state.get("persona") == "tenaga_medis" or state.get("intent") == "medical_information":
            state.setdefault("specialist_guidance", []).append(
                "Jangan mengarang dosis atau ICD-10; tampilkan ADME, interaksi, kontraindikasi, monitoring, dan keterbatasan hanya bila terverifikasi."
            )
        return state
