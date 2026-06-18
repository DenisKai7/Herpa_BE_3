from enum import StrEnum


class ModelMode(StrEnum):
    FAST_MEDIUM = "fast-medium"
    THINKING_HIGH = "thinking-high"


class ApplicationRole(StrEnum):
    ADMIN = "admin"
    USER = "user"


class Persona(StrEnum):
    UMUM = "umum"
    PELAJAR = "pelajar"
    PENELITI = "peneliti"
    TENAGA_MEDIS = "tenaga_medis"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class MessageRole(StrEnum):
    USER = "user"
    AI = "ai"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class GroundingStatus(StrEnum):
    GROUNDED = "grounded"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"
