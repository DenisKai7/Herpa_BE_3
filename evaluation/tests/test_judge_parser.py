"""Regression tests for LLM Judge JSON parsing and score extraction.

Tests ensure:
  - answer_relevancy is ALWAYS returned as float 0.0–1.0
  - Never None, never missing keys
  - Handles all LLM output formats (A, B, C, D, E)
  - Backward compatibility: old 6-metric JSON is handled gracefully
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from evaluation.metrics.batch_judge import (
    _normalize_to_metrics,
    _extract_score_safe,
    _validate_and_fill_scores,
    _parse_json_robust,
    JudgeResult,
    _METRIC_KEYS,
)


# ─── _extract_score_safe ─────────────────────────────────────────────────────

class TestExtractScoreSafe:
    """Always returns float 0.0–1.0, never None."""

    def test_nested_dict_score(self):
        data = {"answer_relevancy": {"score": 0.9, "reason": "good"}}
        assert _extract_score_safe(data, "answer_relevancy") == 0.9

    def test_flat_numeric(self):
        data = {"answer_relevancy": 0.85}
        assert _extract_score_safe(data, "answer_relevancy") == 0.85

    def test_missing_key_returns_zero(self):
        data = {}
        assert _extract_score_safe(data, "answer_relevancy") == 0.0

    def test_null_value_returns_zero(self):
        data = {"answer_relevancy": None}
        assert _extract_score_safe(data, "answer_relevancy") == 0.0

    def test_string_number(self):
        data = {"answer_relevancy": "0.75"}
        assert _extract_score_safe(data, "answer_relevancy") == 0.75

    def test_string_not_number(self):
        data = {"answer_relevancy": "high"}
        assert _extract_score_safe(data, "answer_relevancy") == 0.0

    def test_nested_dict_missing_score_key(self):
        data = {"answer_relevancy": {"reason": "good"}}
        assert _extract_score_safe(data, "answer_relevancy") == 0.0

    def test_clamps_to_0_1(self):
        assert _extract_score_safe({"x": 1.5}, "x") == 1.0
        assert _extract_score_safe({"x": -0.5}, "x") == 0.0

    def test_integer_score(self):
        data = {"answer_relevancy": 1}
        assert _extract_score_safe(data, "answer_relevancy") == 1.0


# ─── _normalize_to_metrics ───────────────────────────────────────────────────

class TestNormalizeToMetrics:
    """Normalizes LLM output formats to standard dict."""

    def test_format_a_nested(self):
        data = {"answer_relevancy": {"score": 0.9, "reason": "good"}}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_format_b_flat_numeric(self):
        data = {"answer_relevancy": 0.9}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_format_c_single_score(self):
        """Single {"score": 1.0} maps to answer_relevancy."""
        data = {"score": 1.0, "reason": "excellent"}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"] == {"score": 1.0, "reason": "excellent"}

    def test_format_e_partial(self):
        data = {"answer_relevancy": {"score": 0.9}}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_empty_dict(self):
        assert _normalize_to_metrics({}) == {}

    def test_none_values_preserved(self):
        data = {"answer_relevancy": None}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"] is None

    def test_backward_compat_old_6_metrics(self):
        """Old 6-metric JSON still parses — only answer_relevancy is used."""
        data = {
            "answer_relevancy": {"score": 0.9},
            "faithfulness": {"score": 0.8},
            "contextual_precision": {"score": 0.7},
        }
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9
        # Old metrics are parsed but ignored by _validate_and_fill_scores


# ─── _validate_and_fill_scores ───────────────────────────────────────────────

class TestValidateAndFillScores:
    """Ensures all metric keys exist as float 0.0–1.0."""

    def test_all_keys_present(self):
        scores = {k: 0.8 for k in _METRIC_KEYS}
        result = _validate_and_fill_scores(scores)
        assert len(result) == len(_METRIC_KEYS)
        assert all(isinstance(v, float) for v in result.values())

    def test_missing_keys_filled_zero(self):
        scores = {"answer_relevancy": 0.9}
        result = _validate_and_fill_scores(scores)
        assert result["answer_relevancy"] == 0.9

    def test_none_values_filled_zero(self):
        scores = {"answer_relevancy": None}
        result = _validate_and_fill_scores(scores)
        assert result["answer_relevancy"] == 0.0

    def test_clamps_out_of_range(self):
        scores = {k: 1.5 for k in _METRIC_KEYS}
        result = _validate_and_fill_scores(scores)
        assert all(v == 1.0 for v in result.values())

    def test_empty_dict(self):
        result = _validate_and_fill_scores({})
        assert len(result) == len(_METRIC_KEYS)
        assert all(v == 0.0 for v in result.values())


# ─── _parse_json_robust ─────────────────────────────────────────────────────

class TestParseJsonRobust:
    """6-stage JSON parser handles all LLM output formats."""

    def test_valid_json(self):
        text = '{"answer_relevancy": {"score": 0.9}}'
        result = _parse_json_robust(text)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_markdown_fenced(self):
        text = '```json\n{"answer_relevancy": {"score": 0.9}}\n```'
        result = _parse_json_robust(text)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_trailing_comma(self):
        text = '{"answer_relevancy": {"score": 0.9},}'
        result = _parse_json_robust(text)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_truncated_json(self):
        text = '{"answer_relevancy": {"score": 0.9'
        result = _parse_json_robust(text)
        assert "answer_relevancy" in result

    def test_text_before_json(self):
        text = 'Here is my evaluation: {"answer_relevancy": {"score": 0.9}}'
        result = _parse_json_robust(text)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_single_score_format(self):
        text = '{"score": 1.0, "reason": "excellent"}'
        result = _parse_json_robust(text)
        assert result["score"] == 1.0

    def test_empty_string(self):
        assert _parse_json_robust("") == {}

    def test_no_json(self):
        assert _parse_json_robust("no json here") == {}


# ─── JudgeResult ─────────────────────────────────────────────────────────────

class TestJudgeResult:
    """JudgeResult has only answer_relevancy as primary metric."""

    def test_default_scores_are_zero(self):
        r = JudgeResult()
        assert r.answer_relevancy == 0.0

    def test_to_dict_all_floats(self):
        r = JudgeResult(answer_relevancy=0.9)
        d = r.to_dict()
        assert all(isinstance(v, float) for v in d.values())
        assert len(d) == 1

    def test_metric_names(self):
        r = JudgeResult()
        assert len(r.metric_names) == 1
        assert "answer_relevancy" in r.metric_names

    def test_valid_score_count(self):
        r = JudgeResult(answer_relevancy=0.9)
        assert r.valid_score_count == 1

    def test_valid_score_count_zero(self):
        r = JudgeResult(answer_relevancy=0.0)
        assert r.valid_score_count == 0

    def test_skipped_result(self):
        r = JudgeResult(skipped=True, skip_reason="Empty answer", success=False)
        assert r.skipped is True
        assert r.success is False
        assert r.answer_relevancy == 0.0


# ─── End-to-end: normalize → extract → validate ─────────────────────────────

class TestEndToEnd:
    """Full pipeline: parse → normalize → extract → validate → JudgeResult."""

    def _run_pipeline(self, raw_text: str) -> JudgeResult:
        data = _parse_json_robust(raw_text)
        data = _normalize_to_metrics(data)
        scores = {
            "answer_relevancy": _extract_score_safe(data, "answer_relevancy"),
        }
        scores = _validate_and_fill_scores(scores)
        return JudgeResult(
            answer_relevancy=scores["answer_relevancy"],
        )

    def test_format_a_full(self):
        text = '{"answer_relevancy":{"score":0.9,"reason":"good"}}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 0.9

    def test_format_b_flat(self):
        text = '{"answer_relevancy":0.9}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 0.9

    def test_format_c_single_score(self):
        text = '{"score": 1.0, "reason": "excellent"}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 1.0

    def test_format_e_partial(self):
        text = '{"answer_relevancy": {"score": 0.9}}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 0.9

    def test_null_values(self):
        text = '{"answer_relevancy": null}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 0.0

    def test_no_json(self):
        r = self._run_pipeline("no json here")
        assert r.answer_relevancy == 0.0

    def test_all_scores_are_float(self):
        """Critical: no None values anywhere."""
        for text in [
            '{"answer_relevancy":{"score":0.9}}',
            '{"score": 1.0}',
            '{"answer_relevancy": 0.9}',
            '{}',
            'garbage',
        ]:
            r = self._run_pipeline(text)
            for attr in r.metric_names:
                val = getattr(r, attr)
                assert isinstance(val, float), f"{attr} is {type(val)} = {val} for input: {text[:50]}"
                assert 0.0 <= val <= 1.0, f"{attr} = {val} out of range for input: {text[:50]}"

    def test_backward_compat_6_metrics(self):
        """Old 6-metric JSON still works — only answer_relevancy extracted."""
        text = '{"answer_relevancy":{"score":0.9},"faithfulness":{"score":0.8},"contextual_precision":{"score":0.7},"contextual_recall":{"score":0.6},"contextual_relevancy":{"score":0.85},"hallucination":{"score":0.1}}'
        r = self._run_pipeline(text)
        assert r.answer_relevancy == 0.9


# ─── Extended tests ──────────────────────────────────────────────────────────

class TestExtractScoreSafeExtended:
    """Extended tests for _extract_score_safe."""

    def test_nested_dict_with_value_key(self):
        data = {"answer_relevancy": {"value": 0.95}}
        assert _extract_score_safe(data, "answer_relevancy") == 0.95

    def test_nested_dict_with_value_and_score(self):
        data = {"answer_relevancy": {"score": 0.9, "value": 0.8}}
        assert _extract_score_safe(data, "answer_relevancy") == 0.9

    def test_nested_dict_with_only_reason(self):
        data = {"answer_relevancy": {"reason": "good"}}
        assert _extract_score_safe(data, "answer_relevancy") == 0.0


class TestNormalizeToMetricsExtended:
    """Extended tests for _normalize_to_metrics."""

    def test_format_d_nested_metrics(self):
        data = {"metrics": {"answer_relevancy": 0.9}}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_format_d_nested_metrics_with_score(self):
        data = {"metrics": {"answer_relevancy": {"score": 0.9, "reason": "good"}}}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["score"] == 0.9

    def test_format_a_with_value_key(self):
        data = {"answer_relevancy": {"value": 0.9, "reason": "good"}}
        result = _normalize_to_metrics(data)
        assert result["answer_relevancy"]["value"] == 0.9


class TestContextBuilder:
    """Tests for evaluation context builder."""

    def test_build_context_from_facts(self):
        from evaluation.context_builder import build_evaluation_context
        retrieval = {
            "entities": [{"canonical_name": "Curcuma longa", "original_text": "kunyit"}],
            "facts": [{
                "plant": {"local_name": "Kunyit", "scientific_name": "Curcuma longa"},
                "compounds": [{"name": "Curcumin"}],
                "therapeutic_uses": [{"name": "Anti-inflammatory"}],
            }],
        }
        contexts, diagnostics = build_evaluation_context(retrieval, "Apa manfaat kunyit?")
        assert len(contexts) > 0
        assert diagnostics["total_chars"] > 0

    def test_build_context_from_entities(self):
        from evaluation.context_builder import build_evaluation_context
        retrieval = {
            "entities": [
                {"canonical_name": "Curcuma longa", "original_text": "kunyit", "entity_type": "herb"},
            ],
            "facts": [],
        }
        contexts, diagnostics = build_evaluation_context(retrieval, "Apa manfaat kunyit?")
        assert len(contexts) > 0

    def test_build_context_empty_retrieval(self):
        from evaluation.context_builder import build_evaluation_context
        contexts, diagnostics = build_evaluation_context({}, "test query")
        assert len(contexts) == 0


class TestJudgeResultExtended:
    """Extended tests for JudgeResult."""

    def test_valid_score_count_excludes_zero(self):
        r = JudgeResult(answer_relevancy=0.0)
        assert r.valid_score_count == 0

    def test_to_dict_all_floats_even_with_zero(self):
        r = JudgeResult(answer_relevancy=0.0)
        d = r.to_dict()
        assert all(isinstance(v, float) for v in d.values())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
