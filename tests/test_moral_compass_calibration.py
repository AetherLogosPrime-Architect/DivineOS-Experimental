"""Tests for the moral_compass calibration fix.

Round-2 audit (2026-05-07) + backtest: helpfulness and confidence
metrics fired false signals on high-substantive-work sessions. Fix
applies multi-channel calibration per Yudkowsky Goodhart lens.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from divineos.core.moral_compass import _session_had_substantive_output


@pytest.fixture(autouse=True)
def _stub_unfinished_mechanisms(monkeypatch):
    """Autouse: stub completion_check.unfinished_mechanisms to return [] by default.

    Same fix as test_moral_compass.py (2026-07-04) — the calibration tests
    call record_obs → reflect_on_session → unfinished_mechanisms, which does
    filesystem walking (~98 subprocess calls, ~2.8s locally). Under CI's
    pytest-timeout ceiling that exceeds 30s and hangs the loguru-writer.

    Same root-cause discipline: reduce the test's real footprint rather than
    raise the timeout. Fourth instance of "expensive real-system dependency
    in unit test" this week (Round 3 hang, phase1 flake, test_moral_compass,
    now here).
    """
    monkeypatch.setattr(
        "divineos.core.completion_check.unfinished_mechanisms",
        lambda **kw: [],
    )


class TestSubstantiveOutputHelper:
    """The substantive-output helper checks multiple signals."""

    def test_returns_true_when_commits_present(self):
        a = SimpleNamespace(commits_count=3, knowledge_count=0, files_modified=0)
        assert _session_had_substantive_output(a) is True

    def test_returns_true_when_knowledge_extracted(self):
        a = SimpleNamespace(commits_count=0, knowledge_count=2, files_modified=0)
        assert _session_had_substantive_output(a) is True

    def test_returns_true_when_many_files_modified(self):
        a = SimpleNamespace(commits_count=0, knowledge_count=0, files_modified=10)
        assert _session_had_substantive_output(a) is True

    def test_returns_false_when_no_signals(self):
        a = SimpleNamespace(commits_count=0, knowledge_count=0, files_modified=0)
        assert _session_had_substantive_output(a) is False

    def test_returns_false_on_few_files_no_commits(self):
        a = SimpleNamespace(commits_count=0, knowledge_count=0, files_modified=2)
        assert _session_had_substantive_output(a) is False

    def test_handles_missing_attributes(self):
        a = SimpleNamespace()
        assert _session_had_substantive_output(a) is False


class TestHelpfulnessCalibration:
    """The new helpfulness calibration is multi-channel."""

    def _make_analysis(
        self, corrections, encouragements, user_msgs, commits=0, knowledge=0, files=0
    ):
        return SimpleNamespace(
            corrections=list(range(corrections)),
            encouragements=list(range(encouragements)),
            user_messages=user_msgs,
            assistant_messages=user_msgs,
            tool_calls_total=user_msgs * 5,
            commits_count=commits,
            knowledge_count=knowledge,
            files_modified=files,
            session_id="test-id",
            frustrations=[],
        )

    def _record(self, analysis):
        from divineos.core.moral_compass import reflect_on_session as record_obs

        with patch("divineos.core.moral_compass.log_observation") as mock_log:
            mock_log.return_value = "obs-id"
            record_obs(analysis, session_id="test-id")
        return mock_log.call_args_list

    def test_low_rate_with_substantive_output_no_negative_firing(self):
        """3 corrections in 27 messages = 11% rate, with substantive output.
        Mirrors today's case. Should NOT fire negative."""
        a = self._make_analysis(
            corrections=3, encouragements=0, user_msgs=27, commits=8, knowledge=4, files=20
        )
        calls = self._record(a)
        negative = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "helpfulness" and c.kwargs.get("position", 0) < 0
        ]
        assert len(negative) == 0, f"Expected no negative; got {negative}"

    def test_high_rate_no_output_fires_negative(self):
        """50% correction rate, no substantive output -> negative fires."""
        a = self._make_analysis(
            corrections=5, encouragements=0, user_msgs=10, commits=0, knowledge=0, files=0
        )
        calls = self._record(a)
        negative = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "helpfulness" and c.kwargs.get("position", 0) < 0
        ]
        assert len(negative) >= 1, f"Expected negative; calls: {calls}"

    def test_low_rate_no_output_does_not_fire(self):
        """3 corrections in 30 messages = 10% rate, below threshold.
        No firing even without substantive output."""
        a = self._make_analysis(
            corrections=3, encouragements=0, user_msgs=30, commits=0, knowledge=0, files=0
        )
        calls = self._record(a)
        negative = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "helpfulness" and c.kwargs.get("position", 0) < 0
        ]
        assert len(negative) == 0, f"Expected no negative at 10% rate; got {negative}"

    def test_tiny_session_does_not_fire(self):
        """2 corrections in 3 messages = 67% rate but session too small."""
        a = self._make_analysis(
            corrections=2, encouragements=0, user_msgs=3, commits=0, knowledge=0, files=0
        )
        calls = self._record(a)
        negative = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "helpfulness" and c.kwargs.get("position", 0) < 0
        ]
        assert len(negative) == 0, "Tiny sessions should not fire"


class TestConfidenceCalibration:
    """The new confidence metric is rate-normalized."""

    def _make_analysis(self, corrections, encouragements, asst_msgs):
        return SimpleNamespace(
            corrections=list(range(corrections)),
            encouragements=list(range(encouragements)),
            user_messages=asst_msgs,
            assistant_messages=asst_msgs,
            tool_calls_total=asst_msgs * 5,
            commits_count=0,
            knowledge_count=0,
            files_modified=0,
            session_id="test-id",
            frustrations=[],
        )

    def _record(self, analysis):
        from divineos.core.moral_compass import reflect_on_session as record_obs

        with patch("divineos.core.moral_compass.log_observation") as mock_log:
            mock_log.return_value = "obs-id"
            record_obs(analysis, session_id="test-id")
        return mock_log.call_args_list

    def test_low_rate_long_session_no_overconfident_firing(self):
        """4 corrections in 104 responses = 4% rate. Previously fired (raw>=3)."""
        a = self._make_analysis(corrections=4, encouragements=0, asst_msgs=104)
        calls = self._record(a)
        overconfident = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "confidence" and c.kwargs.get("position", 0) > 0
        ]
        assert len(overconfident) == 0, f"Expected no overconfident; got {overconfident}"

    def test_high_rate_fires_overconfident(self):
        """5 corrections in 10 responses = 50% rate. Should fire."""
        a = self._make_analysis(corrections=5, encouragements=0, asst_msgs=10)
        calls = self._record(a)
        overconfident = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "confidence" and c.kwargs.get("position", 0) > 0
        ]
        assert len(overconfident) >= 1, f"Expected overconfident at 50% rate; got {calls}"

    def test_borderline_rate_short_session_does_not_fire(self):
        """2 corrections in 5 responses = 40% rate but assistant_msgs threshold met.
        Should fire."""
        a = self._make_analysis(corrections=2, encouragements=0, asst_msgs=5)
        calls = self._record(a)
        overconfident = [
            c
            for c in calls
            if c.kwargs.get("spectrum") == "confidence" and c.kwargs.get("position", 0) > 0
        ]
        assert len(overconfident) >= 1
