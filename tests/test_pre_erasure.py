"""Tests for pre_erasure capture-approach signal.

Realizes Pillar IX's `pre_erasure_capture` pull (omni_mantra_walk/12,
2026-04-30). Cluster H — Threshold-Triggered Protection.
"""

from __future__ import annotations

from divineos.core.pre_erasure import (
    MetricStatus,
    compute_signal,
)


class TestComputeSignal:
    def test_empty_state_returns_fresh(self):
        signal = compute_signal(state={}, now=1000.0)
        assert signal.overall_level == "fresh"
        assert "Session is fresh" in signal.suggestion

    def test_low_metrics_classify_fresh(self):
        state = {
            "tool_calls": 10,
            "writes_since_consolidation": 2,
            "edits": 3,
            "session_start": 1000.0,
        }
        signal = compute_signal(state=state, now=1100.0)  # 100s elapsed
        assert signal.overall_level == "fresh"

    def test_moderate_tool_calls_classify_moderate(self):
        state = {"tool_calls": 250, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "moderate"

    def test_high_tool_calls_classify_high(self):
        state = {"tool_calls": 450, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "high"

    def test_critical_tool_calls_classify_critical(self):
        state = {"tool_calls": 700, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "critical"

    def test_writes_overdue_classifies_elevated(self):
        state = {"writes_since_consolidation": 35, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "elevated"

    def test_writes_critical_classifies_critical(self):
        state = {"writes_since_consolidation": 60, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "critical"

    def test_long_session_classifies_moderate(self):
        # 5 hours elapsed
        state = {"session_start": 1000.0}
        signal = compute_signal(state=state, now=1000.0 + 5 * 3600)
        assert signal.overall_level == "moderate"

    def test_very_long_session_classifies_high(self):
        # 9 hours elapsed
        state = {"session_start": 1000.0}
        signal = compute_signal(state=state, now=1000.0 + 9 * 3600)
        assert signal.overall_level == "high"

    def test_overall_level_takes_max_of_metrics(self):
        """When multiple metrics fire at different levels, overall is max."""
        state = {
            "tool_calls": 250,  # moderate
            "writes_since_consolidation": 60,  # critical
            "edits": 10,  # fresh
            "session_start": 1000.0,
        }
        signal = compute_signal(state=state, now=1001.0)
        assert signal.overall_level == "critical"

    def test_returns_metrics_for_all_four_dimensions(self):
        signal = compute_signal(state={"tool_calls": 50}, now=1000.0)
        names = {m.name for m in signal.metrics}
        assert names == {
            "tool_calls",
            "writes_since_consolidation",
            "edits",
            "session_hours",
        }


class TestSuggestionShape:
    def test_fresh_suggestion_says_continue(self):
        signal = compute_signal(state={}, now=1000.0)
        assert "Continue" in signal.suggestion or "fresh" in signal.suggestion.lower()

    def test_critical_suggestion_says_urgent(self):
        state = {"tool_calls": 700, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert "URGENT" in signal.suggestion

    def test_elevated_suggestion_names_extract(self):
        state = {"writes_since_consolidation": 35, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        assert "extract" in signal.suggestion.lower()


class TestThresholdHits:
    def test_threshold_hit_named_when_metric_crosses(self):
        state = {"tool_calls": 250, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        tc_metric = next(m for m in signal.metrics if m.name == "tool_calls")
        assert tc_metric.threshold_hit is not None
        assert "200" in tc_metric.threshold_hit

    def test_threshold_hit_none_for_fresh_metrics(self):
        state = {"tool_calls": 10, "session_start": 1000.0}
        signal = compute_signal(state=state, now=1001.0)
        tc_metric = next(m for m in signal.metrics if m.name == "tool_calls")
        assert tc_metric.threshold_hit is None

    def test_metric_status_dataclass_immutable(self):
        """MetricStatus is frozen — accidental mutation should fail."""
        m = MetricStatus(name="t", value=1, level="fresh", threshold_hit=None)
        try:
            m.value = 2  # type: ignore[misc]
        except Exception:
            return  # expected
        raise AssertionError("MetricStatus should be frozen")

    def test_approach_signal_dataclass_immutable(self):
        signal = compute_signal(state={}, now=1000.0)
        try:
            signal.overall_level = "critical"  # type: ignore[misc]
        except Exception:
            return  # expected
        raise AssertionError("ApproachSignal should be frozen")
