"""Unit tests for the isolated Ragas evaluation engine.

Tests cover model validation, default test cases, and the evaluation
pipeline's error handling — without requiring Neo4j, LLM, or Ragas.
"""

from app.evaluation.ragas_engine import (
    DEFAULT_TEST_CASES,
    EvaluationResult,
    EvaluationTestCase,
    _build_eval_llm,
)


class TestEvaluationTestCase:
    def test_valid_case(self):
        case = EvaluationTestCase(question="Apa itu jahe?", ground_truth="Jahe adalah tanaman herbal.")
        assert case.question == "Apa itu jahe?"
        assert case.ground_truth == "Jahe adalah tanaman herbal."

    def test_question_required(self):
        import pytest
        with pytest.raises(Exception):
            EvaluationTestCase(ground_truth="only ground truth")

    def test_ground_truth_required(self):
        import pytest
        with pytest.raises(Exception):
            EvaluationTestCase(question="only question")


class TestEvaluationResult:
    def test_defaults(self):
        result = EvaluationResult()
        assert result.overall_metrics == {}
        assert result.per_test_case == []
        assert result.test_case_count == 0
        assert result.elapsed_seconds == 0.0
        assert result.csv_path is None
        assert result.error is None

    def test_with_data(self):
        result = EvaluationResult(
            overall_metrics={"faithfulness": 0.85},
            test_case_count=4,
            elapsed_seconds=12.5,
            csv_path="/tmp/report.csv",
        )
        assert result.overall_metrics["faithfulness"] == 0.85
        assert result.test_case_count == 4
        assert result.csv_path == "/tmp/report.csv"


class TestDefaultTestCases:
    def test_has_four_cases(self):
        assert len(DEFAULT_TEST_CASES) == 4

    def test_each_case_has_question_and_ground_truth(self):
        for case in DEFAULT_TEST_CASES:
            assert case.question.strip(), f"Empty question: {case}"
            assert case.ground_truth.strip(), f"Empty ground_truth: {case}"

    def test_questions_are_indonesian(self):
        questions = [c.question for c in DEFAULT_TEST_CASES]
        assert any("jeruk nipis" in q.lower() for q in questions)
        assert any("bawang putih" in q.lower() for q in questions)
        assert any("ginseng" in q.lower() for q in questions)
        assert any("temulawak" in q.lower() for q in questions)

    def test_cases_are_evaluation_test_case_instances(self):
        for case in DEFAULT_TEST_CASES:
            assert isinstance(case, EvaluationTestCase)


class TestBuildEvalLLM:
    def test_returns_none_without_langchain(self, monkeypatch):
        """If langchain_openai is not importable, _build_eval_llm returns None."""
        import unittest.mock

        # Simulate missing langchain_openai by making import fail
        import builtins
        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "langchain_openai":
                raise ImportError("mocked missing")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        class FakeSettings:
            llama_text_base_url = "http://localhost:8080/v1"
            llama_text_model_name = "test-model"
            text_model_timeout_seconds = 30

        result = _build_eval_llm(FakeSettings())
        assert result is None
