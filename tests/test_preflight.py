"""Tests for the preflight check system."""

import json
from pathlib import Path
from unittest.mock import patch

from divineos.core.hud_handoff import preflight_check


class TestPreflightCheck:
    """Test preflight_check() returns correct readiness status."""

    def test_not_ready_when_briefing_missing(self, tmp_path: Path) -> None:
        """Preflight fails when briefing hasn't been loaded."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            result = preflight_check()
            assert result["ready"] is False
            assert result["briefing_loaded"] is False
            # Briefing check should fail
            briefing_check = next(c for c in result["checks"] if c["name"] == "briefing")
            assert briefing_check["passed"] is False

    def test_ready_when_briefing_loaded(self, tmp_path: Path) -> None:
        """Preflight passes when briefing is loaded and fresh."""
        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=5),
        ):
            result = preflight_check()
            assert result["ready"] is True
            assert result["briefing_loaded"] is True

    def test_engagement_check(self, tmp_path: Path) -> None:
        """Engagement check reflects whether thinking tools were used."""
        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=5),
        ):
            # No engagement marker
            result = preflight_check()
            engagement = next(c for c in result["checks"] if c["name"] == "engagement")
            assert engagement["passed"] is False

            # Add engagement marker
            (tmp_path / ".session_engaged").write_text("1000.0")
            result = preflight_check()
            engagement = next(c for c in result["checks"] if c["name"] == "engagement")
            assert engagement["passed"] is True

    def test_goals_check(self, tmp_path: Path) -> None:
        """Goals check reflects whether active goals exist."""
        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=0),
        ):
            # No goals
            result = preflight_check()
            goals = next(c for c in result["checks"] if c["name"] == "goals")
            assert goals["passed"] is False

            # Add goals
            goals_data = [{"text": "Fix the thing", "status": "active"}]
            (tmp_path / "active_goals.json").write_text(json.dumps(goals_data))
            result = preflight_check()
            goals = next(c for c in result["checks"] if c["name"] == "goals")
            assert goals["passed"] is True

    def test_handoff_check(self, tmp_path: Path) -> None:
        """Handoff check reflects whether a handoff note exists."""
        marker = {"loaded_at": 1000.0, "tool_calls_at_load": 0}
        (tmp_path / ".briefing_loaded").write_text(json.dumps(marker))

        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._count_session_tool_calls", return_value=0),
        ):
            # No handoff
            result = preflight_check()
            handoff = next(c for c in result["checks"] if c["name"] == "handoff")
            assert handoff["passed"] is False

            # Add handoff note
            note = {"summary": "Last session went well", "open_threads": []}
            (tmp_path / "handoff_note.json").write_text(json.dumps(note))
            result = preflight_check()
            handoff = next(c for c in result["checks"] if c["name"] == "handoff")
            assert handoff["passed"] is True

    def test_all_checks_present(self, tmp_path: Path) -> None:
        """Preflight always returns all 4 checks."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            result = preflight_check()
            check_names = {c["name"] for c in result["checks"]}
            assert check_names == {"briefing", "engagement", "handoff", "goals", "session_goal"}
