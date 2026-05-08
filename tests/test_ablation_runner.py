"""Tests for scripts/ablation_runner.py (chunk 3 measurement runner)."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.ablation_runner import (  # noqa: E402
    AblationResult,
    MEASUREMENT_DISPATCH,
    NOISE_FILTER_CORPUS,
    measure_noise_filter_on_extraction,
)


class TestCorpusShape:
    def test_corpus_has_both_labels(self):
        labels = {label for _, label in NOISE_FILTER_CORPUS}
        assert "noise" in labels
        assert "signal" in labels

    def test_corpus_balanced(self):
        """Balanced corpus prevents single-label bias in metric."""
        noise = sum(1 for _, lab in NOISE_FILTER_CORPUS if lab == "noise")
        signal = sum(1 for _, lab in NOISE_FILTER_CORPUS if lab == "signal")
        # Allow 2-entry imbalance (15/15 ideal but 14/16 acceptable)
        assert abs(noise - signal) <= 2, f"unbalanced: {noise} noise vs {signal} signal"

    def test_corpus_size_at_least_20(self):
        """Sample size big enough to avoid trivial noise in metrics."""
        assert len(NOISE_FILTER_CORPUS) >= 20


class TestAblationResult:
    def test_format_report_produces_expected_lines(self):
        result = AblationResult(
            mechanism="x",
            workload="y",
            sample_size=10,
            on_metric_label="on",
            on_metric_value=0.5,
            off_metric_label="off",
            off_metric_value=0.0,
            difference=0.5,
            notes=["note1", "note2"],
        )
        report = result.format_report()
        assert "Ablation result: x" in report
        assert "Workload: y" in report
        assert "Sample size: 10" in report
        assert "0.5000" in report
        assert "+0.5000" in report
        assert "note1" in report
        assert "note2" in report

    def test_format_report_handles_empty_notes(self):
        result = AblationResult(
            mechanism="x",
            workload="y",
            sample_size=10,
            on_metric_label="on",
            on_metric_value=0.5,
            off_metric_label="off",
            off_metric_value=0.0,
            difference=0.5,
        )
        report = result.format_report()
        assert "Notes:" not in report


class TestNoiseFilterMeasurement:
    def test_measurement_runs_without_exception(self):
        result = measure_noise_filter_on_extraction("synthetic")
        assert isinstance(result, AblationResult)

    def test_measurement_metrics_in_unit_range(self):
        result = measure_noise_filter_on_extraction("synthetic")
        assert 0.0 <= result.on_metric_value <= 1.0
        assert 0.0 <= result.off_metric_value <= 1.0

    def test_off_baseline_is_zero(self):
        """With toggle on, the filter is bypassed -- nothing should be rejected."""
        result = measure_noise_filter_on_extraction("synthetic")
        assert result.off_metric_value == 0.0, (
            f"toggle bypass failed: off rate = {result.off_metric_value}; "
            "expected 0.0 (filter bypassed = no rejections)"
        )

    def test_on_filter_does_some_work(self):
        """Filter ON should reject SOMETHING from the noise corpus."""
        result = measure_noise_filter_on_extraction("synthetic")
        assert result.on_metric_value > 0.0

    def test_difference_equals_on_minus_off(self):
        result = measure_noise_filter_on_extraction("synthetic")
        # When OFF is 0, difference equals ON
        assert abs(result.difference - result.on_metric_value) < 1e-9

    def test_notes_include_per_label_breakdown(self):
        result = measure_noise_filter_on_extraction("synthetic")
        notes_text = " ".join(result.notes)
        assert "True positives" in notes_text or "true positives" in notes_text.lower()
        assert "False positives" in notes_text or "false positives" in notes_text.lower()

    def test_unknown_workload_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown workload"):
            measure_noise_filter_on_extraction("unknown")


class TestDispatch:
    def test_noise_filter_in_dispatch(self):
        assert "noise_filter_on_extraction" in MEASUREMENT_DISPATCH

    def test_dispatch_callable(self):
        fn = MEASUREMENT_DISPATCH["noise_filter_on_extraction"]
        assert callable(fn)


class TestWatchmenMeasurement:
    def test_runs_without_exception(self):
        from scripts.ablation_runner import measure_watchmen_self_trigger_prevention

        result = measure_watchmen_self_trigger_prevention("synthetic")
        assert result.mechanism == "watchmen_self_trigger_prevention"

    def test_on_rate_is_one(self):
        """All internal actors should be rejected when validation is ON."""
        from scripts.ablation_runner import measure_watchmen_self_trigger_prevention

        result = measure_watchmen_self_trigger_prevention("synthetic")
        assert result.on_metric_value == 1.0, "expected 100% rejection of internal actors"

    def test_off_rate_is_zero(self):
        """Toggle bypasses validation -- nothing rejected."""
        from scripts.ablation_runner import measure_watchmen_self_trigger_prevention

        result = measure_watchmen_self_trigger_prevention("synthetic")
        assert result.off_metric_value == 0.0

    def test_difference_is_one(self):
        from scripts.ablation_runner import measure_watchmen_self_trigger_prevention

        result = measure_watchmen_self_trigger_prevention("synthetic")
        assert result.difference == 1.0


class TestFamilyOperatorsMeasurement:
    def test_runs_without_exception(self):
        from scripts.ablation_runner import measure_family_voice_appropriation_operators

        result = measure_family_voice_appropriation_operators("synthetic")
        assert result.mechanism == "family_voice_appropriation_operators"

    def test_on_rate_around_half(self):
        """Half the corpus is should_block, so ON rate ~0.5."""
        from scripts.ablation_runner import measure_family_voice_appropriation_operators

        result = measure_family_voice_appropriation_operators("synthetic")
        assert 0.4 <= result.on_metric_value <= 0.6

    def test_off_rate_is_zero(self):
        from scripts.ablation_runner import measure_family_voice_appropriation_operators

        result = measure_family_voice_appropriation_operators("synthetic")
        assert result.off_metric_value == 0.0


class TestDispatchExpanded:
    def test_three_mechanisms_in_dispatch(self):
        from scripts.ablation_runner import MEASUREMENT_DISPATCH

        assert "noise_filter_on_extraction" in MEASUREMENT_DISPATCH
        assert "watchmen_self_trigger_prevention" in MEASUREMENT_DISPATCH
        assert "family_voice_appropriation_operators" in MEASUREMENT_DISPATCH
