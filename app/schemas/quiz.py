from typing import Any, Literal

from pydantic import BaseModel, Field

QuizQuestionType = Literal[
    "multiple_choice",
    "matching",
    "true_false",
    "short_answer",
    "case_based",
]


class QuizLevelResponse(BaseModel):
    id: str
    topic_id: str
    level_number: int
    title: str
    description: str | None = None
    quiz_type: str
    xp_reward: int = 10
    passing_score: int = 70
    is_locked: bool = False
    is_completed: bool = False
    progress: int = 0


class QuizTopicResponse(BaseModel):
    id: str
    title: str
    description: str | None = None
    order_index: int = 0
    icon: str | None = None
    progress: int = 0
    highest_level_completed: int = 0
    current_level: int = 1
    status: str = "available"
    levels: list[QuizLevelResponse] = Field(default_factory=list)


class QuizQuestionResponse(BaseModel):
    id: str
    topic_id: str
    level_id: str
    question_type: QuizQuestionType
    prompt: str
    options: list[Any] = Field(default_factory=list)
    matching_pairs: list[Any] = Field(default_factory=list)
    difficulty: str = "easy"


class StartQuizSessionRequest(BaseModel):
    topic_id: str
    level_id: str | None = None
    level_number: int | None = Field(default=None, ge=1, le=5)


class QuizSessionResponse(BaseModel):
    id: str
    topic_id: str
    level_id: str
    status: str
    score: int = 0
    total_questions: int = 0
    current_question_index: int = 0
    questions: list[QuizQuestionResponse] = Field(default_factory=list)


class SubmitAnswerRequest(BaseModel):
    question_id: str
    answer: Any


class SubmitAnswerResponse(BaseModel):
    correct: bool
    correct_answer: Any | None = None
    explanation: str | None = None
    score_delta: int = 0
    xp_delta: int = 0
    session_completed: bool = False
    session_score: int = 0
    correct_count: int = 0
    wrong_count: int = 0
    total_questions: int = 0
    next_question_index: int | None = None
    passed: bool | None = None
    next_level_unlocked: bool = False


class QuizProgressResponse(BaseModel):
    total_xp: int = 0
    level: int = 1
    completed_topics: int = 0
    completed_levels: int = 0
    current_streak: int = 0
    topic_progress: list[dict[str, Any]] = Field(default_factory=list)
