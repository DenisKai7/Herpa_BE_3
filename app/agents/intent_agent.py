from app.agents.state import AgentState


class IntentAgent:
    async def run(self, state: AgentState) -> AgentState:
        text = state.get("user_query", "").lower()
        has_plant_vlm = any(
            ctx.get("plant_candidates")
            for ctx in state.get("attachment_context", [])
        )
        if has_plant_vlm or any(x in text for x in [
            "tanaman apa", "identifikasi", "tanaman ini", "gambar ini",
            "foto ini", "daun apa", "bunga apa", "ini apa", "nama tanaman",
            "jenis daun", "ini daun apa", "ini tanaman apa", "gambar apa"
        ]):
            intent = "image_identification"
        elif any(x in text for x in ["gejala", "keluhan", "rekomendasi", "meringankan"]):
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
