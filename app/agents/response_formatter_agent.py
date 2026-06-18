from app.agents.state import AgentState


class ResponseFormatterAgent:
    async def run(self, state: AgentState) -> AgentState:
        answer = (state.get("draft_answer") or "").strip()
        if state.get("grounding_status") == "insufficient":
            warnings = [str(item) for item in state.get("warnings", []) if item]
            limitation = warnings[0] if warnings else "Data untuk bagian yang diminta belum tersedia pada sumber yang digunakan."
            if limitation not in answer:
                answer = f"{answer}\n\n{limitation}".strip()
        if state.get("intent") in {"recommendation", "medical_information"}:
            disclaimer = (
                "Informasi ini bersifat edukatif dan bukan diagnosis atau pengganti tenaga kesehatan."
            )
            if disclaimer not in answer:
                answer = f"{answer}\n\n{disclaimer}".strip()
        state["grounded_answer"] = answer
        return state
