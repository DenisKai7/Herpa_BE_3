from typing import Any, Literal
from pydantic import BaseModel, Field

QuestionType = Literal[
    "multiple_choice",
    "multiple_answer",
    "true_false",
    "matching",
    "ordering",
    "fill_blank",
    "formula",
    "structure",
]


class QuizOption(BaseModel):
    id: str
    label: str
    text: str


class QuizQuestion(BaseModel):
    id: str
    question: str
    question_type: QuestionType = "multiple_choice"
    options: list[QuizOption] = Field(default_factory=list)
    explanation: str | None = None
    media_url: str | None = None
    points: int = 10


class QuizAttemptCreate(BaseModel):
    level_id: str
    question_count: int = Field(default=10, ge=5, le=30)


class QuizAnswerRequest(BaseModel):
    question_id: str
    selected_option_ids: list[str] = Field(default_factory=list)
    text_answer: str | None = None
    skipped: bool = False
    duration_ms: int = Field(default=0, ge=0)


class QuizCompletion(BaseModel):
    score: int
    total_questions: int
    accuracy: float
    correct: int
    incorrect: int
    skipped: int
    xp_earned: int
    level_completed: bool
    next_level_unlocked: bool
    analisis_performa: dict[str, list[str]]
    details: list[dict[str, Any]] = Field(default_factory=list)
