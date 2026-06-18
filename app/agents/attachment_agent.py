from app.agents.state import AgentState


class AttachmentAgent:
    async def run(self, state: AgentState) -> AgentState:
        contexts = state.setdefault("attachment_context", [])
        state["attachment_summary"] = {
            "count": len(contexts),
            "types": sorted({str(item.get("detected_type", "unknown")) for item in contexts}),
        }
        return state
