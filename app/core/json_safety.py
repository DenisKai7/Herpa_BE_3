from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from neo4j.time import Date, DateTime, Duration, Time
from pydantic import BaseModel


def json_safe(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, DateTime):
        return value.iso_format()

    if isinstance(value, Date):
        return value.iso_format()

    if isinstance(value, Time):
        return value.iso_format()

    if isinstance(value, Duration):
        return str(value)

    if isinstance(value, BaseModel):
        return json_safe(value.model_dump(mode="python"))

    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]

    if hasattr(value, "items"):
        return {str(key): json_safe(item) for key, item in value.items()}

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)
