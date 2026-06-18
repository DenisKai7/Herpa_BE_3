import re
from app.agents.state import AgentState

RED_FLAGS = {
    "nyeri dada": "Nyeri dada dapat memerlukan evaluasi darurat.",
    "sesak berat": "Sesak berat memerlukan bantuan medis segera.",
    "tidak sadar": "Penurunan kesadaran memerlukan bantuan darurat.",
    "kejang": "Kejang memerlukan evaluasi medis segera.",
    "perdarahan": "Perdarahan berat memerlukan bantuan medis segera.",
    "wajah mencong": "Tanda stroke memerlukan layanan darurat.",
    "bicara pelo": "Tanda stroke memerlukan layanan darurat.",
    "alergi berat": "Reaksi alergi berat memerlukan layanan darurat.",
}


class SafetyAgent:
    async def run(self, state: AgentState) -> AgentState:
        text = state.get("user_query", "").lower()
        flags = []
        for term, message in RED_FLAGS.items():
            if re.search(rf"\b{re.escape(term)}\b", text):
                flags.append(message)
        state["red_flags"] = flags
        state["safety_flags"] = []
        return state
