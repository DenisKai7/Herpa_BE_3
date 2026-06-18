from app.agents.state import AgentState


class IntentAgent:
    async def run(self, state: AgentState) -> AgentState:
        text = state.get("user_query", "").lower()
        if any(x in text for x in ["gejala", "keluhan", "rekomendasi", "meringankan"]):
            intent = "recommendation"
        elif any(x in text for x in ["quiz", "kuis", "soal", "periodik", "stoikiometri"]):
            intent = "education"
        elif any(
            x in text
            for x in ["hplc", "gc-ms", "in vitro", "in-vivo", "isolasi", "penelitian", "jurnal", "pubmed"]
        ):
            intent = "research"
        elif any(x in text for x in ["dosis", "adme", "farmakokinetik", "icd-10", "interaksi obat"]):
            intent = "medical_information"
        else:
            intent = "herbal_information"
        state["intent"] = intent
        state["sub_intents"] = []
        return state
