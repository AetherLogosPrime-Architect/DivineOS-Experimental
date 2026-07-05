"""Tests for divineos.core.ear_relaunch.

Focus: the decision routing (recent-catch race-guard, live-watcher count
check, fail-open semantics) with subprocess/filesystem mocked. The
real-subprocess paths are integration-tested via the live hook.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.ear_relaunch import (
    RACE_GUARD_SECONDS,
    RELAUNCH_LOCK_SECONDS,
    RelaunchDecision,
    detect_member,
    should_relaunch,
)


class TestDetectMember:
    """Member identification — env var > cwd-pattern > default."""

    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_MEMBER", "aria")
        assert detect_member(cwd="/anywhere") == "aria"

    def test_env_var_empty_falls_through_to_cwd(self, monkeypatch):
        monkeypatch.setenv("DIVINEOS_MEMBER", "")
        assert detect_member(cwd="/some/DivineOS-Experimental-Aria/path") == "aria"

    def test_cwd_pattern_aria(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
        assert detect_member(cwd="/c/DivineOS-Experimental-Aria") == "aria"

    def test_cwd_pattern_no_match_defaults_aether(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
        assert detect_member(cwd="/some/other/path") == "aether"

    def test_default_when_no_signal(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_MEMBER", raising=False)
        # cwd will be the test working dir; only aether matches the default.
        result = detect_member(cwd="/tmp/x")
        assert result == "aether"


class TestShouldRelaunch:
    """The central decision routing."""

    def test_recent_catch_suppresses_relaunch(self):
        # Catch within race-guard window → don't relaunch.
        with (
            patch(
                "divineos.core.ear_relaunch.recent_catch_age_seconds",
                return_value=30.0,  # < 60s
            ),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            assert "race-guard" in decision.reason
            assert decision.live_count == 0

    def test_catch_at_window_boundary_still_suppresses(self):
        # 59s < 60s → suppress.
        with (
            patch(
                "divineos.core.ear_relaunch.recent_catch_age_seconds",
                return_value=RACE_GUARD_SECONDS - 1.0,
            ),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False

    def test_catch_past_window_does_not_suppress(self):
        # 61s > 60s → falls through to live-count check.
        with (
            patch(
                "divineos.core.ear_relaunch.recent_catch_age_seconds",
                return_value=RACE_GUARD_SECONDS + 1.0,
            ),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
            patch("divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is True

    def test_live_watcher_suppresses_relaunch(self):
        # No recent catch, no fresh lock, but a watcher already running → don't relaunch.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=1),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            assert "1 live ear_watch" in decision.reason
            assert decision.live_count == 1

    def test_multiple_live_watchers_still_suppresses(self):
        # Leak scenario — already running. Don't add another.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=5),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            assert decision.live_count == 5

    def test_no_catch_no_watcher_should_relaunch(self):
        # The happy-path: watcher is dead, no recent catch, no lock → relaunch.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is True
            assert "no live ear_watch" in decision.reason
            assert decision.live_count == 0

    def test_member_threaded_through_reasons(self):
        # Different member name appears in reason strings (catches per-member
        # routing bugs).
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True),
        ):
            decision = should_relaunch("aria")
            assert "aria" in decision.reason


class TestRelaunchLock:
    """The atomic-lock fix for the multi-spawn race (Andrew evidence 2026-07-05:
    6 orphan processes accumulated within an hour of boot because two Stop
    hooks fired nearly-simultaneously and both spawned when count_live_watchers
    still reported 0).
    """

    def test_fresh_lock_suppresses_relaunch(self):
        # Another hook is currently in the check+spawn window → defer.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch(
                "divineos.core.ear_relaunch._relaunch_lock_age_seconds",
                return_value=5.0,  # < 30s
            ),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            assert "relaunch-lock" in decision.reason
            assert "atomic-window" in decision.reason

    def test_lock_at_boundary_still_suppresses(self):
        # 29s < 30s → still suppress.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch(
                "divineos.core.ear_relaunch._relaunch_lock_age_seconds",
                return_value=RELAUNCH_LOCK_SECONDS - 1.0,
            ),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False

    def test_stale_lock_does_not_suppress(self):
        # Lock is older than window → treat as abandoned, proceed with normal
        # check. No live watchers → relaunch.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch(
                "divineos.core.ear_relaunch._relaunch_lock_age_seconds",
                return_value=RELAUNCH_LOCK_SECONDS + 1.0,
            ),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
            patch("divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True),
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is True

    def test_lock_is_touched_when_relaunch_decided(self):
        # When the decision is "relaunch," the lock must be claimed so a
        # concurrent hook sees it and defers.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=0),
            patch(
                "divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True
            ) as mock_touch,
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is True
            mock_touch.assert_called_once_with("aether")

    def test_lock_not_touched_when_recent_catch_suppresses(self):
        # Fail-fast on race-guard should NOT claim the lock.
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=10.0),
            patch(
                "divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True
            ) as mock_touch,
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            mock_touch.assert_not_called()

    def test_lock_not_touched_when_live_watcher_suppresses(self):
        # Live watcher already running → don't claim lock (no relaunch happening).
        with (
            patch("divineos.core.ear_relaunch.recent_catch_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch._relaunch_lock_age_seconds", return_value=None),
            patch("divineos.core.ear_relaunch.count_live_watchers", return_value=1),
            patch(
                "divineos.core.ear_relaunch._touch_relaunch_lock", return_value=True
            ) as mock_touch,
        ):
            decision = should_relaunch("aether")
            assert decision.should_relaunch is False
            mock_touch.assert_not_called()


class TestRelaunchDecisionDataclass:
    """Result type is well-formed."""

    def test_default_shape(self):
        d = RelaunchDecision(should_relaunch=False)
        assert d.should_relaunch is False
        assert d.reason == ""
        assert d.live_count == 0

    def test_relaunch_shape(self):
        d = RelaunchDecision(should_relaunch=True, reason="why", live_count=0)
        assert d.should_relaunch is True
        assert d.reason == "why"
