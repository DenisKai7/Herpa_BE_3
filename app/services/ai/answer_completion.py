import re

_TRAILING_CONNECTORS = {
    "dan",
    "atau",
    "yang",
    "dengan",
    "untuk",
    "karena",
    "sebagai",
    "pada",
    "dalam",
    "serta",
    "tetapi",
    "namun",
    "meliputi",
    "antara",
    "dari",
}


def is_incomplete_answer(text: str, finish_reason: str | None) -> bool:
    if finish_reason == "length":
        return True
    stripped = (text or "").strip()
    if not stripped:
        return True
    if stripped.endswith((".", "!", "?", ")", "]")):
        return False
    last_word = re.sub(r"[^\wÀ-ÿ-]", "", stripped.split()[-1].lower()) if stripped.split() else ""
    if last_word in _TRAILING_CONNECTORS:
        return True
    if re.search(r"[-•*]\s+[^\n.?!]{1,120}$", stripped):
        return True
    if re.search(r"\b(terbuk|pengguna|aktivitas biologis terbuk)$", stripped.lower()):
        return True
    return len(stripped) > 80 and not re.search(r"[.!?][\s\])]*$", stripped)
