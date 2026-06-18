import pytest
from pydantic import BaseModel
from app.core.exceptions import AppError
from app.services.ai.structured_output import parse_json_model


class Output(BaseModel):
    value: int


def test_parses_fenced_json():
    assert parse_json_model('```json\n{"value": 2}\n```', Output).value == 2


def test_rejects_invalid_json():
    with pytest.raises(AppError):
        parse_json_model("not-json", Output)
