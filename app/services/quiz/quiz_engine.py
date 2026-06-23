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


def normalize_text(value: Any) -> str:
    return " ".join(str(value).strip().lower().split())


def _answer_payload(correct_answer: Any) -> Any:
    if isinstance(correct_answer, dict) and "answer" in correct_answer:
        return correct_answer["answer"]
    return correct_answer


def _accepted_answers(correct_answer: Any, accepted_answers: list[Any] | None = None) -> list[Any]:
    answers = []
    if isinstance(correct_answer, dict):
        answers.extend(correct_answer.get("accepted_answers") or [])
    answers.extend(accepted_answers or [])
    return answers


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
        answers = [expected, *_accepted_answers(correct_answer, accepted_answers)]
        return normalize_text(user_answer) in {normalize_text(answer) for answer in answers}
    if question_type == "matching":
        return normalize_matching_answer(user_answer) == normalize_matching_answer(expected)
    if question_type == "case_based":
        return normalize_text(user_answer) == normalize_text(expected)
    return False
