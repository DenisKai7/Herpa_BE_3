from app.core.constants import ModelMode, Persona
from app.core.exceptions import AppError

_MODEL_MODE_ALIASES = {
    "fast": ModelMode.FAST_MEDIUM,
    "medium": ModelMode.FAST_MEDIUM,
    "fast_medium": ModelMode.FAST_MEDIUM,
    "fast-medium": ModelMode.FAST_MEDIUM,
    "thinking": ModelMode.THINKING_HIGH,
    "hard": ModelMode.THINKING_HIGH,
    "high": ModelMode.THINKING_HIGH,
    "thinking_hard": ModelMode.THINKING_HIGH,
    "thinking-hard": ModelMode.THINKING_HIGH,
    "thinking_high": ModelMode.THINKING_HIGH,
    "thinking-high": ModelMode.THINKING_HIGH,
}

_PERSONA_ALIASES = {
    "umum": Persona.UMUM,
    "general": Persona.UMUM,
    "pelajar": Persona.PELAJAR,
    "student": Persona.PELAJAR,
    "peneliti": Persona.PENELITI,
    "oeneliti": Persona.PENELITI,
    "researcher": Persona.PENELITI,
    "tenaga_medis": Persona.TENAGA_MEDIS,
    "tenaga-medis": Persona.TENAGA_MEDIS,
    "medical": Persona.TENAGA_MEDIS,
}


def normalize_model_mode(value: str | ModelMode | None) -> ModelMode:
    if isinstance(value, ModelMode):
        return value
    key = (value or ModelMode.FAST_MEDIUM.value).strip().lower()
    key = key.replace(" ", "_")
    mode = _MODEL_MODE_ALIASES.get(key)
    if mode is None:
        raise AppError(
            "VALIDATION_ERROR",
            "Model mode tidak valid.",
            422,
            {"field": "model_choice", "allowed": [m.value for m in ModelMode]},
        )
    return mode


def normalize_persona(value: str | Persona | None, fallback: str | Persona | None = None) -> Persona:
    if isinstance(value, Persona):
        return value
    if isinstance(fallback, Persona) and not value:
        return fallback
    raw = value or fallback or Persona.UMUM.value
    key = str(raw).strip().lower().replace(" ", "_")
    persona = _PERSONA_ALIASES.get(key)
    if persona is None:
        return Persona.UMUM
    return persona
