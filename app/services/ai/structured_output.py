import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.exceptions import AppError

T = TypeVar("T", bound=BaseModel)


def parse_json_model(text: str, model: type[T]) -> T:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return model.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AppError(
            "MODEL_OUTPUT_INVALID",
            "Output terstruktur model tidak valid.",
            502,
        ) from exc
