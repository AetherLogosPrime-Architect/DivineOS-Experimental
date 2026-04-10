"""Tests for the periodic engagement system.

The engagement gate is NOT one-and-done. It decays after N code-changing
actions (Edit/Write/Bash) without consulting the OS. This forces mid-session
re-engagement instead of just one ask/recall at the start.
"""

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.hud_handoff import (
    _ENGAGEMENT_DECAY_THRESHOLD,
    clear_engagement,
    engagement_status,
    is_engaged,
    mark_engaged,
    record_code_action,
)


class TestPeriodicEngagement:
    """The core behavior: engagement decays after code actions."""

    def test_not_engaged_when_no_marker(self, tmp_path: Path) -> None:
        """No marker = not engaged."""
        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            assert is_engaged() is False

    def test_engaged_after_mark(self, tmp_path: Path) -> None:
        """mark_engaged() sets engagement."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            mark_engaged()
            assert is_engaged() is True

    def test_engagement_decays_after_code_actions(self, tmp_path: Path) -> None:
        """After enough code actions without OS queries, engagement expires."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            mark_engaged()
            assert is_engaged() is True

            # Simulate code actions up to threshold
            for i in range(_ENGAGEMENT_DECAY_THRESHOLD):
                record_code_action()

            # Now engagement should be expired
            assert is_engaged() is False

    def test_os_query_resets_counter(self, tmp_path: Path) -> None:
        """Using an OS tool (mark_engaged) resets the code action counter."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            mark_engaged()

            # 7 code actions (just under threshold of 8)
            for _ in range(_ENGAGEMENT_DECAY_THRESHOLD - 1):
                record_code_action()
            assert is_engaged() is True

            # Re-engage with OS — counter resets
            mark_engaged()

            # Now we have a fresh budget of 8 code actions
            status = engagement_status()
            assert status["code_actions_since"] == 0
            assert status["remaining"] == _ENGAGEMENT_DECAY_THRESHOLD
            assert is_engaged() is True

    def test_engagement_status_shows_remaining(self, tmp_path: Path) -> None:
        """engagement_status() shows how many actions remain before block."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            mark_engaged()

            status = engagement_status()
            assert status["engaged"] is True
            assert status["code_actions_since"] == 0
            assert status["remaining"] == _ENGAGEMENT_DECAY_THRESHOLD

            # After 3 code actions
            for _ in range(3):
                record_code_action()

            status = engagement_status()
            assert status["engaged"] is True
            assert status["code_actions_since"] == 3
            assert status["remaining"] == _ENGAGEMENT_DECAY_THRESHOLD - 3

    def test_engagement_status_when_expired(self, tmp_path: Path) -> None:
        """engagement_status() shows expired state correctly."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            mark_engaged()
            for _ in range(_ENGAGEMENT_DECAY_THRESHOLD + 2):
                record_code_action()

            status = engagement_status()
            assert status["engaged"] is False
            assert status["code_actions_since"] == _ENGAGEMENT_DECAY_THRESHOLD + 2
            assert status["remaining"] == 0

    def test_clear_engagement(self, tmp_path: Path) -> None:
        """clear_engagement() removes the marker entirely."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            mark_engaged()
            assert is_engaged() is True
            clear_engagement()
            assert is_engaged() is False

    def test_record_code_action_noop_without_marker(self, tmp_path: Path) -> None:
        """record_code_action() does nothing if no engagement marker exists."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            # Should not raise
            record_code_action()
            assert is_engaged() is False


class TestOldFormatCompatibility:
    """Old engagement marker was just a timestamp string. New format is JSON."""

    def test_old_format_treated_as_engaged(self, tmp_path: Path) -> None:
        """Old-format markers (plain timestamp) are treated as engaged."""
        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            (tmp_path / ".session_engaged").write_text("1711800000.0")
            assert is_engaged() is True

    def test_old_format_status_shows_engaged(self, tmp_path: Path) -> None:
        """Old-format markers show full engagement in status."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            (tmp_path / ".session_engaged").write_text("1711800000.0")
            status = engagement_status()
            assert status["engaged"] is True
            assert status["remaining"] == _ENGAGEMENT_DECAY_THRESHOLD

    def test_old_format_upgraded_on_code_action(self, tmp_path: Path) -> None:
        """record_code_action() upgrades old format to new JSON format."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            (tmp_path / ".session_engaged").write_text("1711800000.0")
            record_code_action()

            # Should now be new format
            marker = json.loads((tmp_path / ".session_engaged").read_text())
            assert isinstance(marker, dict)
            assert marker["code_actions_since"] == 1

    def test_old_format_upgraded_on_mark_engaged(self, tmp_path: Path) -> None:
        """mark_engaged() always writes new format regardless of old state."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            (tmp_path / ".session_engaged").write_text("1711800000.0")
            mark_engaged()

            marker = json.loads((tmp_path / ".session_engaged").read_text())
            assert isinstance(marker, dict)
            assert marker["code_actions_since"] == 0


class TestPreflight:
    """Preflight check integrates with periodic engagement."""

    def test_preflight_shows_remaining_actions(self, tmp_path: Path) -> None:
        """Preflight detail message includes remaining action count."""
        from divineos.core.hud_handoff import preflight_check

        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=5),
        ):
            # Engage with new format
            mark_engaged()
            for _ in range(3):
                record_code_action()

            result = preflight_check()
            engagement = next(c for c in result["checks"] if c["name"] == "engagement")
            assert engagement["passed"] is True
            assert "code actions before next check-in" in engagement["detail"]

    def test_preflight_shows_expired_engagement(self, tmp_path: Path) -> None:
        """Preflight shows expired engagement with action count."""
        from divineos.core.hud_handoff import preflight_check

        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=5),
            patch(
                "divineos.core.hud_handoff._active_threshold",
                return_value=_ENGAGEMENT_DECAY_THRESHOLD,
            ),
        ):
            mark_engaged()
            for _ in range(_ENGAGEMENT_DECAY_THRESHOLD + 1):
                record_code_action()

            result = preflight_check()
            engagement = next(c for c in result["checks"] if c["name"] == "engagement")
            assert engagement["passed"] is False
            assert "code actions without OS consultation" in engagement["detail"]


class TestPreflightCompassIntegrity:
    """Preflight checks compass integrity automatically."""

    def test_preflight_includes_compass_check(self, tmp_path: Path) -> None:
        """Compass integrity appears as a preflight check."""
        from divineos.core.hud_handoff import preflight_check

        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=0),
        ):
            mark_engaged()
            result = preflight_check()
            compass_check = next(
                (c for c in result["checks"] if c["name"] == "compass_integrity"),
                None,
            )
            assert compass_check is not None
            assert compass_check["passed"] is True
            assert "intact" in compass_check["detail"]


class TestThresholdValue:
    """The threshold should be reasonable — not too tight, not too loose."""

    def test_threshold_is_15(self) -> None:
        """15 code actions before re-engagement is required."""
        assert _ENGAGEMENT_DECAY_THRESHOLD == 15


class TestContextAwareThreshold:
    """Engagement threshold adapts to commit flows."""

    def test_base_threshold_when_no_staged_files(self, tmp_path: Path) -> None:
        """Without staged files, use the base threshold."""
        from divineos.core.hud_handoff import _active_threshold

        # Mock git returning 0 (no staged changes) and no flow state
        with (
            patch("subprocess.run") as mock_run,
            patch("divineos.core.hud_handoff._is_flow_state", return_value=False),
        ):
            mock_run.return_value.returncode = 0
            assert _active_threshold() == _ENGAGEMENT_DECAY_THRESHOLD

    def test_commit_threshold_when_staged_files(self, tmp_path: Path) -> None:
        """With staged files, use the higher commit threshold."""
        from divineos.core.hud_handoff import (
            _ENGAGEMENT_COMMIT_THRESHOLD,
            _active_threshold,
        )

        # Mock git returning 1 (staged changes exist) and no flow state
        with (
            patch("subprocess.run") as mock_run,
            patch("divineos.core.hud_handoff._is_flow_state", return_value=False),
        ):
            mock_run.return_value.returncode = 1
            assert _active_threshold() == _ENGAGEMENT_COMMIT_THRESHOLD

    def test_commit_threshold_is_double_base(self) -> None:
        """Commit threshold gives twice the room for mechanical work."""
        from divineos.core.hud_handoff import _ENGAGEMENT_COMMIT_THRESHOLD

        assert _ENGAGEMENT_COMMIT_THRESHOLD == 30
        assert _ENGAGEMENT_COMMIT_THRESHOLD == 2 * _ENGAGEMENT_DECAY_THRESHOLD

    def test_is_engaged_uses_commit_threshold_during_staging(self, tmp_path: Path) -> None:
        """During commit flow, 20 actions should still be engaged."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value.returncode = 1  # staged files exist
            mark_engaged()

            # 20 actions — past base threshold (15) but under commit threshold (30)
            for _ in range(20):
                record_code_action()

            assert is_engaged() is True  # would be False without context awareness

    def test_falls_back_to_base_on_git_error(self, tmp_path: Path) -> None:
        """If git is unavailable, use base threshold."""
        from divineos.core.hud_handoff import _active_threshold

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch("divineos.core.hud_handoff._is_flow_state", return_value=False),
        ):
            assert _active_threshold() == _ENGAGEMENT_DECAY_THRESHOLD


class TestFlowState:
    """Flow state detection — high velocity work loops get higher threshold."""

    def test_flow_state_detected_at_high_velocity(self, tmp_path: Path) -> None:
        """Rapid actions (< 10s apart on average) trigger flow state."""
        from divineos.core.hud_handoff import _is_flow_state

        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            # Simulate: engaged 30 seconds ago, 10 actions since → 3s per action
            marker = {
                "engaged_at": 1000.0,
                "code_actions_since": 10,
                "last_action_at": 1030.0,
            }
            (tmp_path / ".session_engaged").write_text(json.dumps(marker))
            assert _is_flow_state() is True

    def test_no_flow_state_at_low_velocity(self, tmp_path: Path) -> None:
        """Slow actions (> 10s apart) are not flow state."""
        from divineos.core.hud_handoff import _is_flow_state

        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            # Simulate: engaged 300 seconds ago, 10 actions since → 30s per action
            marker = {
                "engaged_at": 1000.0,
                "code_actions_since": 10,
                "last_action_at": 1300.0,
            }
            (tmp_path / ".session_engaged").write_text(json.dumps(marker))
            assert _is_flow_state() is False

    def test_no_flow_state_with_few_actions(self, tmp_path: Path) -> None:
        """Need at least 5 actions to detect flow pattern."""
        from divineos.core.hud_handoff import _is_flow_state

        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            marker = {
                "engaged_at": 1000.0,
                "code_actions_since": 3,
                "last_action_at": 1005.0,
            }
            (tmp_path / ".session_engaged").write_text(json.dumps(marker))
            assert _is_flow_state() is False

    def test_flow_state_raises_threshold(self, tmp_path: Path) -> None:
        """Flow state pushes threshold to 50."""
        from divineos.core.hud_handoff import _FLOW_STATE_THRESHOLD, _active_threshold

        with (
            patch("divineos.core.hud_handoff._is_flow_state", return_value=True),
        ):
            assert _active_threshold() == _FLOW_STATE_THRESHOLD

    def test_flow_state_threshold_value(self) -> None:
        """Flow state threshold is 50."""
        from divineos.core.hud_handoff import _FLOW_STATE_THRESHOLD

        assert _FLOW_STATE_THRESHOLD == 50

    def test_no_flow_state_without_marker(self, tmp_path: Path) -> None:
        """No engagement marker = no flow state."""
        from divineos.core.hud_handoff import _is_flow_state

        with patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path):
            assert _is_flow_state() is False

    def test_flow_state_keeps_agent_engaged(self, tmp_path: Path) -> None:
        """In flow state, 20 actions should still be engaged."""
        import time as _time

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            mark_engaged()

            # Simulate rapid-fire actions by writing the marker directly
            marker = {
                "engaged_at": _time.time() - 20,  # started 20s ago
                "code_actions_since": 20,
                "last_action_at": _time.time(),  # last action now
            }
            (tmp_path / ".session_engaged").write_text(json.dumps(marker))

            # 20 actions in 20 seconds = 1s per action → flow state
            # Should be engaged despite exceeding base threshold (15)
            assert is_engaged() is True
