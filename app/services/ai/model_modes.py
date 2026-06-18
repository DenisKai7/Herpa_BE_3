from dataclasses import dataclass

from app.core.config import Settings
from app.core.constants import ModelMode, Persona


@dataclass(frozen=True)
class ModeProfile:
    name: ModelMode
    max_output_tokens: int
    retrieval_limit: int
    compound_limit: int
    therapeutic_use_limit: int
    protein_target_limit: int
    source_limit: int
    temperature: float
    top_p: float
    top_k: int
    repeat_penalty: float
    allow_external_tools: bool
    allow_refinement: bool
    max_history_messages: int
    max_context_tokens: int
    graph_cache_ttl_seconds: int
    refinement_max_tokens: int = 0


def mode_profile(settings: Settings, mode: ModelMode, persona: Persona) -> ModeProfile:
    if mode == ModelMode.THINKING_HIGH:
        return ModeProfile(
            name=mode,
            max_output_tokens=_thinking_high_tokens(settings, persona),
            retrieval_limit=settings.thinking_high_retrieval_limit,
            compound_limit=settings.thinking_high_compound_limit,
            therapeutic_use_limit=settings.thinking_high_use_limit,
            protein_target_limit=settings.thinking_high_target_limit,
            source_limit=settings.thinking_high_source_limit,
            temperature=settings.thinking_high_temperature,
            top_p=settings.thinking_high_top_p,
            top_k=settings.thinking_high_top_k,
            repeat_penalty=settings.thinking_high_repeat_penalty,
            allow_external_tools=True,
            allow_refinement=True,
            max_history_messages=settings.thinking_high_max_history_messages,
            max_context_tokens=settings.thinking_high_max_context_tokens,
            graph_cache_ttl_seconds=settings.thinking_high_graph_cache_ttl_seconds,
            refinement_max_tokens=settings.thinking_high_refinement_max_tokens,
        )
    return ModeProfile(
        name=mode,
        max_output_tokens=_fast_medium_tokens(settings, persona),
        retrieval_limit=settings.fast_medium_retrieval_limit,
        compound_limit=settings.fast_medium_compound_limit,
        therapeutic_use_limit=settings.fast_medium_use_limit,
        protein_target_limit=settings.fast_medium_target_limit,
        source_limit=settings.fast_medium_source_limit,
        temperature=settings.fast_medium_temperature,
        top_p=settings.fast_medium_top_p,
        top_k=settings.fast_medium_top_k,
        repeat_penalty=settings.fast_medium_repeat_penalty,
        allow_external_tools=False,
        allow_refinement=False,
        max_history_messages=settings.fast_medium_max_history_messages,
        max_context_tokens=settings.fast_medium_max_context_tokens,
        graph_cache_ttl_seconds=settings.fast_medium_graph_cache_ttl_seconds,
    )


def _fast_medium_tokens(settings: Settings, persona: Persona) -> int:
    return {
        Persona.UMUM: settings.fast_medium_max_tokens_umum,
        Persona.PELAJAR: settings.fast_medium_max_tokens_pelajar,
        Persona.PENELITI: settings.fast_medium_max_tokens_peneliti,
        Persona.TENAGA_MEDIS: settings.fast_medium_max_tokens_tenaga_medis,
    }[persona]


def _thinking_high_tokens(settings: Settings, persona: Persona) -> int:
    return {
        Persona.UMUM: settings.thinking_high_max_tokens_umum,
        Persona.PELAJAR: settings.thinking_high_max_tokens_pelajar,
        Persona.PENELITI: settings.thinking_high_max_tokens_peneliti,
        Persona.TENAGA_MEDIS: settings.thinking_high_max_tokens_tenaga_medis,
    }[persona]
