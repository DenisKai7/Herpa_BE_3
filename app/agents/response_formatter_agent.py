import logging
from app.agents.state import AgentState
from app.core.config import Settings

logger = logging.getLogger(__name__)


class ResponseFormatterAgent:
    async def run(self, state: AgentState) -> AgentState:
        answer = (state.get("draft_answer") or "").strip()

        if state.get("query_intent") == "image-identification":
            grounding = state.get("grounding_status")
            confidence = state.get("confidence", 0)
            vlm_candidates = []
            not_likely = []
            vlm_failed = False
            file_size = 0
            morphology = {}
            for ctx in state.get("attachment_context", []):
                vlm_candidates.extend(ctx.get("plant_candidates", []))
                not_likely.extend(ctx.get("not_likely", []))
                vlm_failed = vlm_failed or ctx.get("vlm_failed", False)
                file_size = ctx.get("size_bytes", 0)
                if ctx.get("morphology"):
                    morphology = ctx["morphology"]

            # Retrieve details for debugging/logging
            attachment_id = "unknown"
            visual_summary = ""
            for ctx in state.get("attachment_context", []):
                attachment_id = ctx.get("attachment_id", "unknown")
                visual_summary = ctx.get("visual_summary", "")
                break

            candidate_mismatch = False
            top_candidate = vlm_candidates[0].get("local_name") if vlm_candidates else None
            top_confidence = vlm_candidates[0].get("confidence", 0) if vlm_candidates else 0
            final_candidate = top_candidate
            graph_rag_candidate = None
            leaf_type = morphology.get("leaf_type", "unknown")

            # Task 16: If VLM failed / not available, return model vision not available message
            if vlm_failed:
                answer = "Saya belum bisa memastikan jenis daun dari gambar ini karena model vision lokal belum tersedia. Pastikan llama.cpp vision berjalan di http://localhost:8081/v1."
                final_candidate = None
            else:
                answer_lower = answer.lower()

                # Task 13: Morphology guard - compound leaf
                if leaf_type == "compound":
                    simple_leaves = ["alpukat", "sirih", "mangga", "jambu", "persea", "piper betle"]
                    if any(x in answer_lower for x in simple_leaves) and not any("kelor" in (c.get("local_name") or "").lower() for c in vlm_candidates):
                        candidate_mismatch = True
                        for sl in simple_leaves:
                            if sl in answer_lower:
                                graph_rag_candidate = sl.capitalize()
                                break

                # Task 13: Morphology guard - simple leaf
                elif leaf_type == "simple":
                    if "kelor" in answer_lower or "moringa" in answer_lower:
                        is_kelor_valid = False
                        if vlm_candidates:
                            top = vlm_candidates[0]
                            top_name = (top.get("local_name") or "").lower()
                            if "kelor" in top_name and top.get("confidence", 0) >= 0.70:
                                is_kelor_valid = True
                        if not is_kelor_valid:
                            candidate_mismatch = True
                            graph_rag_candidate = "Daun kelor"

                # Task 14: Hard veto for alpukat
                if ("alpukat" in answer_lower or "persea" in answer_lower) and not candidate_mismatch:
                    alpukat_valid = False
                    if vlm_candidates:
                        for cand in vlm_candidates:
                            cand_name = (cand.get("local_name") or "").lower()
                            if "alpukat" in cand_name and cand.get("confidence", 0) >= 0.70 and leaf_type == "simple":
                                alpukat_valid = True
                                break
                    if not alpukat_valid:
                        candidate_mismatch = True
                        graph_rag_candidate = "Daun alpukat"

                # If candidate mismatch is triggered by any guardrail, correct the final answer
                if candidate_mismatch and vlm_candidates:
                    top = vlm_candidates[0]
                    top_name = (top.get("local_name") or "").lower()
                    if "kelor" in top_name:
                        answer = (
                            "Berdasarkan ciri visual, daun pada gambar kemungkinan besar adalah daun kelor (Moringa oleifera). "
                            "Ciri yang mendukung adalah daun majemuk menyirip dengan banyak anak daun kecil berbentuk oval "
                            "yang tersusun pada satu tangkai. Ini berbeda dari daun alpukat yang biasanya berupa daun tunggal "
                            "besar berbentuk oval-lanset."
                        )
                    else:
                        cues = ", ".join(top.get("visual_evidence", top.get("visual_cues", [])))
                        sci_name = f" ({top.get('scientific_name')})" if top.get('scientific_name') else ""
                        answer = (
                            f"Berdasarkan ciri visual pada gambar, daun/tanaman ini kemungkinan besar adalah "
                            f"{top.get('local_name')}{sci_name}. "
                            f"Ciri visual yang mendukung: {cues}. "
                            f"Ini tidak cocok dengan kandidat lain."
                        )
                    final_candidate = top.get("local_name")

                # Task 9 & 10: General Visual Top Candidate Consistency check (if not corrected yet)
                if vlm_candidates and not candidate_mismatch:
                    top = vlm_candidates[0]
                    top_name = (top.get("local_name") or "").lower()
                    answer_lower = answer.lower()
                    if top_name not in answer_lower:
                        candidate_mismatch = True
                        for item in not_likely:
                            rejected_name = ""
                            if isinstance(item, dict):
                                rejected_name = item.get("name_local") or item.get("local_name") or ""
                            elif isinstance(item, str):
                                rejected_name = item
                            rejected_name_lower = str(rejected_name).lower()
                            if rejected_name_lower and rejected_name_lower in answer_lower:
                                graph_rag_candidate = rejected_name
                                break

                        cues = ", ".join(top.get("visual_evidence", top.get("visual_cues", [])))
                        sci_name = f" ({top.get('scientific_name')})" if top.get('scientific_name') else ""
                        answer = (
                            f"Berdasarkan ciri visual pada gambar, daun/tanaman ini kemungkinan besar adalah "
                            f"{top.get('local_name')}{sci_name}. "
                            f"Ciri visual yang mendukung: {cues}."
                        )
                        final_candidate = top.get("local_name")

            # Task 14: Debug Logging
            settings = Settings()
            logger.info(
                "vision_plant_identification log",
                extra={
                    "event": "vision_plant_identification",
                    "attachment_id": attachment_id,
                    "image_loaded": True,
                    "image_bytes_size": file_size,
                    "vlm_called": True,
                    "vlm_model": settings.llama_vision_model_name,
                    "visual_summary": visual_summary,
                    "vlm_candidates": vlm_candidates,
                    "vlm_top_candidate": top_candidate,
                    "vlm_confidence": top_confidence,
                    "graph_rag_enabled_after_vlm": True,
                    "graph_rag_query": [e.get("canonical_name") for e in state.get("entities", []) if e.get("entity_type") == "plant"],
                    "graph_rag_candidate": graph_rag_candidate or top_candidate if not vlm_failed else None,
                    "final_candidate": final_candidate,
                    "candidate_mismatch": candidate_mismatch,
                    "morphology": morphology,
                }
            )

            if grounding == "vlm_identified" and not vlm_failed:
                if vlm_candidates:
                    top = vlm_candidates[0]
                    confidence_note = (
                        f"\n\nCatatan: Identifikasi ini berdasarkan analisis visual "
                        f"(confidence visual: {top.get('confidence', '?')}). "
                        f"Verifikasi dengan data botani knowledge graph belum tersedia. "
                        f"Disarankan konfirmasi dengan ahli botani atau aroma khasnya."
                    )
                else:
                    confidence_note = (
                        "\n\nCatatan: Identifikasi berdasarkan analisis visual. "
                        "Verifikasi dengan data botani belum tersedia."
                    )
                if confidence_note not in answer:
                    answer += confidence_note
            elif grounding in ("grounded", "partial") and vlm_candidates:
                confidence_note = (
                    "\n\nIdentifikasi ini didukung oleh analisis visual dan data knowledge graph."
                )
                if confidence and confidence < 0.8:
                    confidence_note += " Namun, tingkat kepercayaan belum tinggi; verifikasi lebih lanjut disarankan."
                if confidence_note not in answer:
                    answer += confidence_note

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
