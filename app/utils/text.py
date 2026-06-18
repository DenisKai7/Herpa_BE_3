import re


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
