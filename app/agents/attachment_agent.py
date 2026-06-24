from app.agents.state import AgentState


class AttachmentAgent:
    async def run(self, state: AgentState) -> AgentState:
        contexts = state.setdefault("attachment_context", [])
        state["attachment_summary"] = {
            "count": len(contexts),
            "types": sorted({str(item.get("detected_type", "unknown")) for item in contexts}),
        }

        vlm_candidates = []
        for ctx in contexts:
            for candidate in ctx.get("plant_candidates", []):
                name = candidate.get("scientific_name") or candidate.get("local_name")
                if name:
                    vlm_candidates.append({
                        "entity_type": "plant",
                        "canonical_name": candidate.get("scientific_name", name),
                        "original_text": candidate.get("local_name", name),
                        "confidence": candidate.get("confidence", 0.5),
                        "source": "vlm",
                    })

        if vlm_candidates:
            existing = state.get("entities", [])
            existing_names = {e.get("canonical_name", "").lower() for e in existing}
            merged = []
            for vc in vlm_candidates:
                if vc["canonical_name"].lower() not in existing_names:
                    merged.append(vc)
            merged.extend(existing)
            state["entities"] = merged
            state["vlm_plant_candidates"] = vlm_candidates

        return state
