import re
import unicodedata


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def stable_id(prefix: str, value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", normalize_name(value)).strip("_")
    return f"{prefix}:{slug}"
