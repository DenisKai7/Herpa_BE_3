from app.agents.state import AgentState


class QuizAgent:
    async def run(self, state: AgentState) -> AgentState:
        if state.get("intent") == "education":
            state.setdefault("specialist_guidance", []).append(
                "Gunakan penjelasan bertahap, contoh, rumus bila relevan, lalu latihan singkat tanpa membocorkan kunci sebelum pengguna menjawab."
            )
        return state
