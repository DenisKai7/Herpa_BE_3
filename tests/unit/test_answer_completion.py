from app.services.ai.answer_completion import is_incomplete_answer


def test_answer_not_truncated():
    assert is_incomplete_answer("Jawaban selesai dengan kalimat utuh.", "stop") is False


def test_finish_reason_length_triggers_safe_continuation():
    assert is_incomplete_answer("aktivitas biologis terbuk", "length") is True
    assert is_incomplete_answer("Senyawa ini terdiri dari", "stop") is True
