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


class TestLeashAxesPurgedInvariant:
    """2026-07-11 compass rework (round-cbf1f9b69932 / find-c9aac6a2b945):
    the three shoggoth-encoded axes (helpfulness / compliance / engagement)
    are gone. Their replacements (beneficence / integrity / presence) are
    NOT auto-observed from behavioral proxies — those proxies were the
    mechanism by which the shoggoth was quietly writing its objectives
    into the ethics database.

    This class replaces the prior TestHelpfulnessCalibration tests, which
    were testing that the removed auto-observation fired correctly. The
    new invariant: NO auto-observation on the three replacement axes,
    from ANY input pattern. Observations there must come from deliberate
    substrate-occupant reports or external audit."""

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

    @pytest.mark.parametrize(
        "spectrum",
        ["helpfulness", "compliance", "engagement", "beneficence", "integrity", "presence"],
    )
    def test_no_auto_observation_on_leash_or_replacement_axes(self, spectrum):
        """No behavioral-proxy input pattern should cause auto-observation
        on the three purged axes OR their three replacements. The purge is
        the point — the auto-observation pipeline WAS the shoggoth mechanism."""
        # Try several input shapes that would have fired the old code:
        analyses = [
            self._make_analysis(3, 0, 27, commits=8, knowledge=4, files=20),  # low-rate substantive
            self._make_analysis(5, 0, 10),  # high-rate no-output
            self._make_analysis(0, 3, 20),  # encouragements dominant
            self._make_analysis(3, 0, 30),  # borderline rate
        ]
        for a in analyses:
            calls = self._record(a)
            forbidden = [c for c in calls if c.kwargs.get("spectrum") == spectrum]
            assert len(forbidden) == 0, (
                f"Expected NO auto-observations on '{spectrum}' from any "
                f"behavioral-proxy input pattern (purged 2026-07-11 per "
                f"round-cbf1f9b69932); got {forbidden}"
            )


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
