"""Tests for non-interactive-safety fixes on destructive CLI commands.

Three bugs found in 2026-05-05 verification pass:
1. ``commitment clear`` was destructive without confirmation.
2. ``goal reset`` infinite-prompt-looped on non-interactive stdin.
3. ``bio edit`` raised an uncaught FileNotFoundError when EDITOR unset.

This module pins the corrected behavior.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db


@pytest.fixture(autouse=True)
def _isolated_db(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()
    init_knowledge_table()
    yield


def _seed_goals(tmp_path, goals: list[dict]) -> None:
    hud_dir = tmp_path / "hud"
    hud_dir.mkdir(exist_ok=True)
    (hud_dir / "active_goals.json").write_text(json.dumps(goals, indent=2), encoding="utf-8")


class TestCommitmentClear:
    def test_no_commitments_skips_confirmation(self):
        result = CliRunner().invoke(cli, ["commitment", "clear"])
        assert result.exit_code == 0
        assert "No commitments" in result.output

    def test_yes_flag_clears_without_prompt(self):
        from divineos.core.planning_commitments import add_commitment

        add_commitment("test commitment for safety", context="test")
        result = CliRunner().invoke(cli, ["commitment", "clear", "--yes"])
        assert result.exit_code == 0
        assert "Commitments cleared" in result.output

    def test_non_interactive_aborts_without_yes(self):
        from divineos.core.planning_commitments import add_commitment

        add_commitment("test commitment", context="test")
        # CliRunner with no input simulates non-interactive
        result = CliRunner().invoke(cli, ["commitment", "clear"], input="")
        # Should abort, NOT clear
        assert "Commitments cleared" not in result.output

    def test_no_response_to_prompt_aborts(self):
        from divineos.core.planning_commitments import add_commitment

        add_commitment("test commitment", context="test")
        # User answers "n" to confirmation
        result = CliRunner().invoke(cli, ["commitment", "clear"], input="n\n")
        assert result.exit_code != 0 or "Aborted" in result.output


class TestGoalReset:
    def test_no_goals_returns_clean(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        result = CliRunner().invoke(cli, ["goal", "reset"])
        assert result.exit_code == 0
        assert "No goals" in result.output

    def test_yes_flag_resets_without_prompt(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        _seed_goals(tmp_path, [{"text": "g1", "status": "active", "added_at": 1.0}])
        result = CliRunner().invoke(cli, ["goal", "reset", "--yes"])
        assert result.exit_code == 0
        # Verify the file is now empty list
        path = tmp_path / "hud" / "active_goals.json"
        assert json.loads(path.read_text()) == []

    def test_non_interactive_aborts_without_yes(self, tmp_path, monkeypatch):
        """The exact #goal-reset failure mode: empty stdin should not loop."""
        monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
        _seed_goals(tmp_path, [{"text": "g1", "status": "active", "added_at": 1.0}])
        CliRunner().invoke(cli, ["goal", "reset"], input="")
        # Goal should NOT have been removed
        path = tmp_path / "hud" / "active_goals.json"
        goals = json.loads(path.read_text())
        assert len(goals) == 1


class TestBioEditEditorMissing:
    def test_editor_not_found_message(self, monkeypatch):
        """When $EDITOR points at a nonexistent binary, give a graceful error
        instead of a Python traceback."""
        # Force a bogus editor path
        monkeypatch.setenv("EDITOR", "this-editor-definitely-does-not-exist-xyz")
        monkeypatch.delenv("VISUAL", raising=False)
        result = CliRunner().invoke(cli, ["bio", "edit"], input="\n")
        # Should NOT have a traceback
        assert "Traceback" not in result.output
        assert "FileNotFoundError" not in result.output
        # SHOULD have a helpful message
        assert (
            "not found" in result.output.lower()
            or "set $EDITOR" in result.output.lower()
            or "set $editor" in result.output.lower()
        )
        assert result.exit_code != 0
