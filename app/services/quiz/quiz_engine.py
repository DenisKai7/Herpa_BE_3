from __future__ import annotations

from typing import Any


def calculate_user_level(total_xp: int) -> int:
    return max(1, int(total_xp) // 100 + 1)


def calculate_topic_progress(highest_level_completed: int, total_levels: int = 5) -> int:
    """progress_percent = levels passed / total * 100"""
    return min(100, int((max(0, highest_level_completed) / total_levels) * 100))


def is_level_unlocked(level_number: int, highest_level_completed: int) -> bool:
    """Level 1 always unlocked. Level N unlocked if Level N-1 completed with score >= PASSING_SCORE.
    The caller must ensure highest_level_completed only counts levels with best_score >= 70."""
    return level_number <= 1 or highest_level_completed >= level_number - 1


def normalize_matching_answer(value: Any) -> list[tuple[str, str]]:
    if isinstance(value, dict):
        return sorted((str(k).strip().lower(), str(v).strip().lower()) for k, v in value.items())
    if isinstance(value, list):
        pairs = []
        for item in value:
            if isinstance(item, dict):
                left = item.get("left") or item.get("left_id") or item.get("source") or item.get("a")
                right = item.get("right") or item.get("right_id") or item.get("target") or item.get("b")
                if left is not None and right is not None:
                    pairs.append((str(left).strip().lower(), str(right).strip().lower()))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                pairs.append((str(item[0]).strip().lower(), str(item[1]).strip().lower()))
        return sorted(pairs)
    return []


def normalize_answer(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower().strip()
    text = " ".join(text.split())
    for dash in ("‐", "–", "—", "−"):
        text = text.replace(dash, "-")
    return text


def normalize_text(value: Any) -> str:
    return normalize_answer(value)


def _answer_payload(correct_answer: Any) -> Any:
    if isinstance(correct_answer, dict) and "answer" in correct_answer:
        return correct_answer["answer"]
    return correct_answer


def extract_accepted_answers(correct_answer: Any, accepted_answers: list[Any] | None = None) -> list[str]:
    values: list[Any] = []
    if correct_answer is None:
        values = []
    elif isinstance(correct_answer, str):
        values = [correct_answer]
    elif isinstance(correct_answer, list):
        values = [item for item in correct_answer if item is not None]
    elif isinstance(correct_answer, dict):
        for key in ("accepted_answers", "keywords", "answers"):
            item = correct_answer.get(key)
            if isinstance(item, list):
                values.extend(x for x in item if x is not None)
                break
        else:
            for key in ("answer", "value", "correct", "text", "label"):
                item = correct_answer.get(key)
                if isinstance(item, str):
                    values.append(item)
                    break
            else:
                values.append(correct_answer)
    else:
        values = [correct_answer]
    values.extend(accepted_answers or [])

    result = []
    seen = set()
    for value in values:
        text = str(value)
        if not normalize_answer(text):
            continue
        key = normalize_answer(text)
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def format_correct_answer(correct_answer: Any, accepted_answers: list[Any] | None = None) -> str:
    accepted = extract_accepted_answers(correct_answer, accepted_answers)
    return accepted[0] if accepted else ""


def _accepted_answers(correct_answer: Any, accepted_answers: list[Any] | None = None) -> list[Any]:
    return extract_accepted_answers(correct_answer, accepted_answers)


def is_answer_correct(
    question_type: str, correct_answer: Any, user_answer: Any, accepted_answers: list[Any] | None = None
) -> bool:
    expected = _answer_payload(correct_answer)
    if question_type == "multiple_choice":
        return normalize_text(user_answer) == normalize_text(expected)
    if question_type == "true_false":
        if isinstance(expected, str):
            expected = normalize_text(expected) in {"true", "benar", "1", "yes", "ya"}
        if isinstance(user_answer, str):
            user_answer = normalize_text(user_answer) in {"true", "benar", "1", "yes", "ya"}
        return bool(user_answer) == bool(expected)
    if question_type == "short_answer":
        user_normalized = normalize_answer(user_answer)
        if not user_normalized:
            return False
        normalized_answers = [normalize_answer(answer) for answer in extract_accepted_answers(correct_answer, accepted_answers)]
        return user_normalized in normalized_answers or any(
            answer and len(answer) >= 3 and answer in user_normalized for answer in normalized_answers
        )
    if question_type == "matching":
        return normalize_matching_answer(user_answer) == normalize_matching_answer(expected)
    if question_type == "case_based":
        if isinstance(correct_answer, dict) and "keywords" in correct_answer:
            keywords = correct_answer["keywords"]
            min_keywords = correct_answer.get("min_keywords", 1)
            if not user_answer:
                return False
            user_normalized = normalize_text(user_answer)
            match_count = sum(1 for kw in keywords if normalize_text(kw) in user_normalized)
            return match_count >= min_keywords
        return normalize_text(user_answer) == normalize_text(expected)
    return False


def match_case_keywords(correct_answer: Any, user_answer: str) -> tuple[bool, list[str], list[str]]:
    """Returns (is_correct, matched_keywords, required_keywords)."""
    if isinstance(correct_answer, dict):
        keywords = correct_answer.get("required_keywords") or correct_answer.get("keywords") or correct_answer.get("accepted_answers", [])
        min_keywords = correct_answer.get("min_keywords", 1)
    else:
        keywords = extract_accepted_answers(correct_answer)
        min_keywords = 1
    if not user_answer or not keywords:
        return False, [], keywords
    user_normalized = normalize_text(user_answer)
    matched = [kw for kw in keywords if normalize_text(kw) and normalize_text(kw) in user_normalized]
    return len(matched) >= min_keywords, matched, keywords
