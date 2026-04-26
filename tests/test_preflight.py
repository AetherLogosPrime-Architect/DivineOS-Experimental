"""Tests for the preflight check system."""

import json
import time
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
        marker = {"loaded_at": time.time(), "tool_calls_at_load": 0}
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
        marker = {"loaded_at": time.time(), "tool_calls_at_load": 0}
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
        marker = {"loaded_at": time.time(), "tool_calls_at_load": 0}
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
        marker = {"loaded_at": time.time(), "tool_calls_at_load": 0}
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
        """Preflight always returns all 7 checks."""
        with (
            patch("divineos.core.hud_handoff._get_hud_dir", return_value=tmp_path),
            patch("divineos.core.hud_handoff._ensure_hud_dir", return_value=tmp_path),
        ):
            result = preflight_check()
            check_names = {c["name"] for c in result["checks"]}
            assert check_names == {
                "briefing",
                "engagement",
                "handoff",
                "goals",
                "session_goal",
                "compass_integrity",
                "branch_base",
            }


class TestBranchBaseCheck:
    """Soft warning when current branch is behind origin/main (claim 2026-04-24 18:37)."""

    def test_passes_on_main(self, monkeypatch) -> None:
        """When operator is on main itself, the check is not applicable."""
        from divineos.core.hud_handoff import _check_branch_base_fresh

        def fake_run(cmd, **_kwargs):
            class R:
                returncode = 0
                stdout = "main\n"

            return R()

        monkeypatch.setattr("subprocess.run", fake_run)
        passed, detail = _check_branch_base_fresh()
        assert passed
        assert "main" in detail.lower()

    def test_passes_when_origin_main_in_history(self, monkeypatch) -> None:
        """Branch is fresh when origin/main is an ancestor of HEAD."""
        from divineos.core.hud_handoff import _check_branch_base_fresh

        call_log: list[list[str]] = []

        def fake_run(cmd, **_kwargs):
            call_log.append(cmd)

            class R:
                returncode = 0
                stdout = "feature-branch\n" if cmd[1] == "symbolic-ref" else ""

            return R()

        monkeypatch.setattr("subprocess.run", fake_run)
        passed, _ = _check_branch_base_fresh()
        assert passed

    def test_fails_when_branch_behind(self, monkeypatch) -> None:
        """Soft warning fires when origin/main has commits HEAD lacks."""
        from divineos.core.hud_handoff import _check_branch_base_fresh

        def fake_run(cmd, **_kwargs):
            class R:
                returncode = 0
                stdout = ""

            r = R()
            if cmd[1] == "symbolic-ref":
                r.stdout = "feature\n"
            elif cmd[1] == "rev-parse":
                r.returncode = 0
            elif cmd[1] == "merge-base":
                r.returncode = 1  # NOT an ancestor — stale
            elif cmd[1] == "rev-list":
                r.stdout = "5\n"
            return r

        monkeypatch.setattr("subprocess.run", fake_run)
        passed, detail = _check_branch_base_fresh()
        assert not passed
        assert "5" in detail
        assert "rebase" in detail.lower()

    def test_skips_when_git_unavailable(self, monkeypatch) -> None:
        """Soft check: never block readiness when git isn't around."""
        from divineos.core.hud_handoff import _check_branch_base_fresh

        def fake_run(*_a, **_kw):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr("subprocess.run", fake_run)
        passed, detail = _check_branch_base_fresh()
        assert passed
        assert "skipped" in detail.lower()
