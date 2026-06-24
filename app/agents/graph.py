import asyncio
import time

from app.agents.graph_retriever_agent import GraphRetrieverAgent
from app.agents.grounding_validator_agent import GroundingValidatorAgent
from app.agents.response_formatter_agent import ResponseFormatterAgent
from app.agents.state import AgentState
from app.agents.supervisor import SupervisorAgent
from app.core.constants import ModelMode, Persona
from app.core.model_modes import normalize_model_mode, normalize_persona
from app.graph.context_builder import build_graph_context
from app.graph.retriever import GraphRetriever
from app.prompts.graph_rag import graph_rag_prompt
from app.prompts.model_modes import build_system_prompt, refinement_prompt
from app.services.ai.answer_completion import is_incomplete_answer
from app.services.ai.complexity_analyzer import assess_complexity
from app.services.ai.context_budget import fit_messages_to_context
from app.services.ai.direct_answer_engine import build_direct_answer
from app.services.ai.model_gateway import ModelGateway
from app.services.ai.model_modes import mode_profile
from app.services.ai.query_intent import DIRECT_ANSWER_INTENTS, QueryIntent, classify_query_intent


class AgenticGraph:
    def __init__(
        self,
        supervisor: SupervisorAgent,
        retriever: GraphRetriever,
        gateway: ModelGateway,
    ) -> None:
        self.supervisor = supervisor
        self.retriever = retriever
        self.graph_retriever = GraphRetrieverAgent(retriever)
        self.grounding_validator = GroundingValidatorAgent()
        self.response_formatter = ResponseFormatterAgent()
        self.gateway = gateway

    async def run(self, state: AgentState, queue: asyncio.Queue | None = None) -> AgentState:
        mode = normalize_model_mode(state.get("model_mode"))
        persona = normalize_persona(state.get("persona"))
        state["model_mode"] = mode.value
        state["requested_mode"] = mode.value
        state["execution_mode_used"] = mode.value
        state["tools_used"] = []
        state["stage"] = "profile_resolution"
        state["degraded"] = False
        state["model_call_count"] = 0
        started_intent = time.perf_counter()
        intent = classify_query_intent(state.get("user_query", ""))
        state["query_intent"] = intent.value
        state.setdefault("timings", {})["intent_ms"] = int((time.perf_counter() - started_intent) * 1000)

        state = await self.supervisor.prepare(state)
        if state.get("red_flags"):
            state["draft_answer"] = (
                "Gejala yang Anda sebutkan termasuk tanda bahaya. Segera hubungi layanan "
                "darurat atau fasilitas kesehatan terdekat. Sistem tidak akan memberikan "
                "rekomendasi herbal untuk kondisi ini."
            )
            state["grounded_answer"] = state["draft_answer"]
            state["grounding_status"] = "safety_rule"
            state["confidence"] = 1.0
            state["warnings"] = state["red_flags"]
            state["citations"] = []
            return state

        intent = QueryIntent(state.get("query_intent", QueryIntent.GENERAL.value))
        if mode == ModelMode.FAST_MEDIUM and intent in DIRECT_ANSWER_INTENTS:
            direct_state = await self._try_direct_answer(state, persona, queue, intent, ModelMode.FAST_MEDIUM)
            if direct_state is not None:
                return direct_state
        if mode == ModelMode.THINKING_HIGH:
            return await self._run_thinking_high(state, persona, queue)
        return await self._run_fast_medium(state, persona, queue)

    async def _try_direct_answer(
        self,
        state: AgentState,
        persona: Persona,
        queue: asyncio.Queue | None,
        intent: QueryIntent,
        mode: ModelMode,
    ) -> AgentState | None:
        started_total = time.perf_counter()
        profile = mode_profile(self.gateway.settings, mode, persona)
        cache_ttl = (
            self.gateway.settings.thinking_high_herb_cache_ttl_seconds
            if mode == ModelMode.THINKING_HIGH
            else self.gateway.settings.fast_medium_herb_cache_ttl_seconds
        )
        state["stage"] = "direct_retrieval"
        if queue:
            await queue.put(("retrieval.started", {"message": "Mencari data tanaman..."}))
        started_ret = time.perf_counter()
        graph_context = await self.retriever.direct_herb_context(
            state.get("user_query", ""),
            compound_limit=profile.compound_limit,
            source_limit=profile.source_limit,
            cache_ttl=cache_ttl,
        )
        retrieval_ms = int((time.perf_counter() - started_ret) * 1000)
        state.setdefault("timings", {})["retrieval_ms"] = retrieval_ms
        if queue:
            await queue.put(("retrieval.completed", {"grounding_status": "grounded" if graph_context.get("herb") else "insufficient"}))
            await queue.put(("generation.started", {"message": "Menyusun jawaban..."}))
        started_fmt = time.perf_counter()
        direct = await build_direct_answer(
            query=state.get("user_query", ""), intent=intent, persona=persona, graph_context=graph_context
        )
        formatting_ms = int((time.perf_counter() - started_fmt) * 1000)
        state["timings"]["formatting_ms"] = formatting_ms
        if not direct.handled or not direct.answer:
            return None
        if queue:
            state["timings"]["ttft_ms"] = int((time.perf_counter() - started_total) * 1000)
            for chunk in self._chunk_answer(direct.answer):
                await queue.put(("token", {"text": chunk}))
        state["draft_answer"] = direct.answer
        state["grounded_answer"] = direct.answer
        state["citations"] = [source.model_dump() for source in direct.sources]
        state["warnings"] = direct.warnings
        state["confidence"] = 0.95 if direct.grounding_status == "grounded" else 0.75
        state["grounding_status"] = direct.grounding_status
        state["graph_facts"] = [{"plant": graph_context.get("herb", {}), "compounds": graph_context.get("compounds", []), "sources": graph_context.get("sources", [])}]
        state["retrieval"] = graph_context
        state["retrieval_count"] = 1 if graph_context.get("herb") else 0
        state["tools_used"] = []
        state["execution_mode_used"] = "fast-medium-direct" if mode == ModelMode.FAST_MEDIUM else "thinking-high-direct"
        state["direct_answer_used"] = True
        state["model_calls"] = 0
        state["model_call_count"] = 0
        state["refinement_used"] = False
        state["compound_count"] = direct.compound_count
        state["retrieval_source"] = graph_context.get("retrieval_source", "neo4j")
        state["finish_reason"] = "complete"
        state["timings"]["generation_ms"] = 0
        state["timings"]["total_ms"] = int((time.perf_counter() - started_total) * 1000)
        state["latency_ms"] = state["timings"]["total_ms"]
        return state

    @staticmethod
    def _chunk_answer(answer: str) -> list[str]:
        return [part for part in answer.splitlines(keepends=True) if part]

    async def _run_fast_medium(self, state: AgentState, persona, queue: asyncio.Queue | None) -> AgentState:
        profile = mode_profile(self.gateway.settings, ModelMode.FAST_MEDIUM, persona)
        state["stage"] = "neo4j_retrieval"
        state["retrieval_limit"] = profile.retrieval_limit
        state["compound_limit"] = profile.compound_limit
        state["therapeutic_use_limit"] = profile.therapeutic_use_limit
        state["protein_target_limit"] = profile.protein_target_limit
        state["source_limit"] = profile.source_limit

        started_ret = time.perf_counter()
        if queue:
            await queue.put(("retrieval.started", {}))
        state = await self.graph_retriever.run(state)
        state["retrieval_count"] = len(state.get("graph_facts", []))
        state = await self.supervisor.specialize(state)
        state = await self.supervisor.evidence.run(state)
        state["tools_used"] = self._tools_used(state)
        ret_ms = int((time.perf_counter() - started_ret) * 1000)
        state.setdefault("timings", {})["retrieval_ms"] = ret_ms
        if queue:
            await queue.put(
                (
                    "retrieval.completed",
                    {"grounding_status": "grounded" if state["graph_facts"] else "insufficient"},
                )
            )

        messages = self._messages(state, persona, ModelMode.FAST_MEDIUM)
        messages = fit_messages_to_context(
            messages,
            self.gateway.settings.text_model_context_size,
            profile.max_output_tokens,
            self.gateway.settings.text_model_context_safety_margin,
            persona=persona.value,
            user_query=state.get("user_query", ""),
        )

        state["stage"] = "draft_generation"
        state["model_call_count"] += 1
        if state["model_call_count"] > 1:
            raise RuntimeError("Fast Medium may only use one model call")
        started_gen = time.perf_counter()
        if queue:
            await queue.put(("generation.started", {}))
            tokens = []
            ttft_ms = None
            stream_metadata: dict[str, str] = {}
            async for token in self.gateway.stream_text(
                messages, mode=ModelMode.FAST_MEDIUM, persona=persona, stream_metadata=stream_metadata
            ):
                if ttft_ms is None:
                    ttft_ms = int((time.perf_counter() - started_gen) * 1000)
                    state["timings"]["ttft_ms"] = ttft_ms
                tokens.append(token)
                await queue.put(("token", {"text": token}))
            answer = "".join(tokens)
            finish_reason = stream_metadata.get("finish_reason") or "stop"
            latency_ms = int((time.perf_counter() - started_gen) * 1000)
        else:
            result = await self.gateway.generate_text(messages, mode=ModelMode.FAST_MEDIUM, persona=persona)
            answer = result.text
            finish_reason = result.finish_reason or "stop"
            latency_ms = result.latency_ms

        state["finish_reason"] = finish_reason
        if is_incomplete_answer(answer, finish_reason):
            state.setdefault("warnings", []).append("Jawaban model terpotong; dilakukan continuation singkat.")
            continuation, cont_ms = await self._continue_answer(answer, state, persona, ModelMode.FAST_MEDIUM, queue)
            if continuation:
                answer = f"{answer.rstrip()} {continuation.lstrip()}"
                latency_ms += cont_ms
                state["finish_reason"] = "continued"
                state["model_call_count"] += 1
        state["timings"]["generation_ms"] = latency_ms
        state["latency_ms"] = latency_ms
        state["draft_answer"] = answer
        state["citations"] = self._sources(state)

        state["stage"] = "grounding_validation"
        if queue:
            await queue.put(("validation.started", {}))
        state = await self.grounding_validator.run(state)
        state = await self.response_formatter.run(state)
        return state

    async def _run_thinking_high(self, state: AgentState, persona, queue: asyncio.Queue | None) -> AgentState:
        profile = mode_profile(self.gateway.settings, ModelMode.THINKING_HIGH, persona)
        state["stage"] = "neo4j_retrieval"
        state["retrieval_limit"] = profile.retrieval_limit
        state["compound_limit"] = profile.compound_limit
        state["therapeutic_use_limit"] = profile.therapeutic_use_limit
        state["protein_target_limit"] = profile.protein_target_limit
        state["source_limit"] = profile.source_limit

        started_ret = time.perf_counter()
        if queue:
            await queue.put(("retrieval.started", {}))
        state = await self.graph_retriever.run(state)
        state["retrieval_count"] = len(state.get("graph_facts", []))
        state = await self.supervisor.specialize(state)
        intent = QueryIntent(state.get("query_intent", QueryIntent.GENERAL.value))
        assessment = assess_complexity(state["user_query"], persona, intent)
        state["complexity"] = assessment.model_dump()
        if assessment.requires_pubmed or assessment.requires_pubchem or assessment.requires_protein_targets:
            state["stage"] = "external_tools"
            state = await self.supervisor.evidence.run(state)
        state["tools_used"] = self._tools_used(state)
        ret_ms = int((time.perf_counter() - started_ret) * 1000)
        state.setdefault("timings", {})["retrieval_ms"] = ret_ms
        if queue:
            await queue.put(
                (
                    "retrieval.completed",
                    {"grounding_status": "grounded" if state["graph_facts"] else "insufficient"},
                )
            )

        draft_messages = self._messages(state, persona, ModelMode.THINKING_HIGH)
        draft_messages = fit_messages_to_context(
            draft_messages,
            self.gateway.settings.text_model_context_size,
            profile.max_output_tokens,
            self.gateway.settings.text_model_context_safety_margin,
            persona=persona.value,
            user_query=state.get("user_query", ""),
        )

        state["stage"] = "draft_generation"
        state["model_call_count"] += 1
        started_gen = time.perf_counter()
        if queue:
            await queue.put(("generation.started", {}))
            tokens = []
            ttft_ms = None
            stream_metadata: dict[str, str] = {}
            async for token in self.gateway.stream_text(
                draft_messages, mode=ModelMode.THINKING_HIGH, persona=persona, stream_metadata=stream_metadata
            ):
                if ttft_ms is None:
                    ttft_ms = int((time.perf_counter() - started_gen) * 1000)
                    state["timings"]["ttft_ms"] = ttft_ms
                tokens.append(token)
                await queue.put(("token", {"text": token}))
            draft_text = "".join(tokens)
            finish_reason = stream_metadata.get("finish_reason") or "stop"
            latency_ms = int((time.perf_counter() - started_gen) * 1000)
        else:
            draft = await self.gateway.generate_text(
                draft_messages, mode=ModelMode.THINKING_HIGH, persona=persona
            )
            draft_text = draft.text
            finish_reason = draft.finish_reason or "stop"
            latency_ms = draft.latency_ms

        state["finish_reason"] = finish_reason
        if is_incomplete_answer(draft_text, finish_reason):
            state.setdefault("warnings", []).append("Jawaban model terpotong; dilakukan continuation singkat.")
            continuation, cont_ms = await self._continue_answer(draft_text, state, persona, ModelMode.THINKING_HIGH, queue)
            if continuation:
                draft_text = f"{draft_text.rstrip()} {continuation.lstrip()}"
                latency_ms += cont_ms
                state["finish_reason"] = "continued"
                state["model_call_count"] += 1
        state["timings"]["generation_ms"] = latency_ms
        state["latency_ms"] = latency_ms
        state["draft_answer"] = draft_text
        state["citations"] = self._sources(state)

        state["stage"] = "grounding_validation"
        if queue:
            await queue.put(("validation.started", {}))
        state = await self.grounding_validator.run(state)

        requires_refine = assessment.requires_refinement and not (
            intent
            in {
                QueryIntent.COMPOUND_LIST,
                QueryIntent.HERB_IDENTITY,
                QueryIntent.THERAPEUTIC_USE_LIST,
            }
        )

        if not requires_refine:
            state["execution_mode_used"] = "thinking-high-single-pass"
            state["refinement_used"] = False
            state["model_calls"] = state.get("model_call_count", 1)
            state = await self.response_formatter.run(state)
            return state

        # Perform refinement
        review_messages = [
            {"role": "system", "content": build_system_prompt(persona, ModelMode.THINKING_HIGH)},
            {
                "role": "user",
                "content": "\n\n".join(
                    [
                        refinement_prompt(),
                        f"PERTANYAAN ASLI:\n{state['user_query']}",
                        f"DRAFT:\n{draft_text}",
                        f"FAKTA TERVERIFIKASI:\n{build_graph_context(state.get('retrieval', {}), state.get('attachment_context'), state.get('external_evidence'), intent=state.get('query_intent'))}",
                        f"STATUS GROUNDING: {state.get('grounding_status')}",
                    ]
                ),
            },
        ]
        review_messages = fit_messages_to_context(
            review_messages,
            self.gateway.settings.text_model_context_size,
            profile.refinement_max_tokens,
            self.gateway.settings.text_model_context_safety_margin,
            persona=persona.value,
            user_query=state.get("user_query", ""),
        )

        state["stage"] = "refinement_generation"
        state["model_call_count"] += 1
        started_ref = time.perf_counter()
        try:
            if queue:
                await queue.put(("refinement.started", {}))
                tokens = []
                async for token in self.gateway.stream_text(
                    review_messages,
                    mode=ModelMode.THINKING_HIGH,
                    persona=persona,
                    max_tokens=profile.refinement_max_tokens,
                ):
                    tokens.append(token)
                    await queue.put(("token", {"text": token}))
                refined_text = "".join(tokens)
                ref_ms = int((time.perf_counter() - started_ref) * 1000)
            else:
                refined = await self.gateway.generate_text(
                    review_messages,
                    mode=ModelMode.THINKING_HIGH,
                    max_tokens=profile.refinement_max_tokens,
                    persona=persona,
                )
                refined_text = refined.text
                ref_ms = refined.latency_ms

            state["timings"]["refinement_ms"] = ref_ms
            state["latency_ms"] = state.get("latency_ms", 0) + ref_ms
            state["draft_answer"] = refined_text
            state["execution_mode_used"] = "thinking-high-refined"
            state["refinement_used"] = True
            state["model_calls"] = state.get("model_call_count", 2)
            state["stage"] = "grounding_validation"
            if queue:
                await queue.put(("validation.started", {}))
            state = await self.grounding_validator.run(state)
        except Exception:
            state["execution_mode_used"] = "thinking-high-draft-only"
            state["degraded"] = True
            state.setdefault("warnings", []).append("Tahap pemeriksaan akhir tidak berhasil diselesaikan.")

        state = await self.response_formatter.run(state)
        return state

    async def _continue_answer(
        self,
        partial_answer: str,
        state: AgentState,
        persona: Persona,
        mode: ModelMode,
        queue: asyncio.Queue | None,
    ) -> tuple[str, int]:
        prompt = (
            "Lanjutkan hanya kalimat terakhir yang terpotong. "
            "Jangan ulangi isi sebelumnya. Maksimal 2 kalimat. Akhiri dengan kalimat utuh.\n\n"
            f"PERTANYAAN: {state.get('user_query', '')}\n"
            f"POTONGAN JAWABAN:\n{partial_answer[-800:]}"
        )
        messages = [
            {"role": "system", "content": build_system_prompt(persona, mode)},
            {"role": "user", "content": prompt},
        ]
        started = time.perf_counter()
        if queue:
            stream_metadata: dict[str, str] = {}
            tokens: list[str] = []
            async for token in self.gateway.stream_text(
                messages,
                mode=mode,
                persona=persona,
                max_tokens=120,
                stream_metadata=stream_metadata,
            ):
                tokens.append(token)
                await queue.put(("token", {"text": token}))
            return "".join(tokens).strip(), int((time.perf_counter() - started) * 1000)
        result = await self.gateway.generate_text(messages, mode=mode, persona=persona, max_tokens=120)
        return result.text.strip(), result.latency_ms

    def _messages(self, state: AgentState, persona, mode: ModelMode) -> list[dict[str, str]]:
        context = build_graph_context(
            state.get("retrieval", {}),
            state.get("attachment_context"),
            state.get("external_evidence"),
            intent=state.get("query_intent"),
        )
        guidance = "\n".join(f"- {item}" for item in state.get("specialist_guidance", []))
        system = build_system_prompt(persona, mode)
        if guidance:
            system += f"\n\nPANDUAN SPESIALIS:\n{guidance}"
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": graph_rag_prompt(context, state["user_query"], intent=state.get("query_intent"))},
        ]

    @staticmethod
    def _tools_used(state: AgentState) -> list[str]:
        tools: list[str] = []
        for item in state.get("external_evidence", []):
            if "pmid" in item and "pubmed" not in tools:
                tools.append("pubmed")
            if "cid" in item and "pubchem" not in tools:
                tools.append("pubchem")
        return tools

    @staticmethod
    def _sources(state: AgentState) -> list[dict]:
        sources: list[dict] = []
        for item in state.get("external_evidence", []):
            sources.append(
                {
                    "type": "pubmed" if "pmid" in item else "pubchem",
                    "source_id": item.get("source_id", ""),
                    "title": item.get("title") or item.get("name") or item.get("source_id", ""),
                    "url": item.get("url"),
                }
            )
        for index, fact in enumerate(state.get("graph_facts", [])[:10]):
            node = fact.get("plant") or fact.get("compound") or {}
            source_id = node.get("plant_id") or node.get("compound_id") or f"neo4j:{index}"
            sources.append(
                {
                    "type": "neo4j",
                    "source_id": source_id,
                    "title": node.get("scientific_name") or node.get("name") or source_id,
                    "evidence_level": node.get("evidence_level"),
                }
            )
        for attachment in state.get("attachment_context", []):
            sources.append(
                {
                    "type": "attachment",
                    "source_id": attachment.get("attachment_id", ""),
                    "title": attachment.get("filename") or attachment.get("attachment_id", "Attachment"),
                }
            )
        return sources
