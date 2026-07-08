from typing import Any
from pydantic import BaseModel, Field


class QuizModuleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    subject_id: str | None = None
    slug: str | None = None
    sort_order: int = 0
    is_active: bool = True


class QuizModuleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class QuizLevelCreate(BaseModel):
    module_id: str
    title: str = Field(..., min_length=1, max_length=200)
    level_number: int = Field(1, ge=1, le=10)
    passing_score: int = Field(70, ge=0, le=100)
    xp_reward: int = Field(25, ge=0)


class QuizLevelUpdate(BaseModel):
    title: str | None = None
    level_number: int | None = None
    passing_score: int | None = None
    xp_reward: int | None = None


class QuizQuestionCreate(BaseModel):
    level_id: str
    prompt: str = Field(..., min_length=1, max_length=5000)
    question_type: str = "multiple_choice"
    explanation: str = ""
    correct_answer: Any = None
    difficulty: int = Field(1, ge=1, le=5)
    options: list[dict[str, Any]] = Field(default_factory=list)
    is_active: bool = True


class QuizQuestionUpdate(BaseModel):
    prompt: str | None = None
    question_type: str | None = None
    explanation: str | None = None
    correct_answer: Any = None
    difficulty: int | None = None
    is_active: bool | None = None
