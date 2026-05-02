"""Tests that session_start and session_plan survive mid-session extract.

This is the remaining piece of the session-analyzer bug that PR #159 + PR #160
didn't close. PR #159 stopped the per-turn Stop-hook trigger. PR #160 fixed
clear_engagement(). This test file locks the fix for reset_state() and
clear_session_plan() — the other two pipeline-side clearers that had the
same wrong-location pattern.

Root symptom: `divineos extract` produced "Brief session (1 messages)" even
after PR #159, because the pipeline's finally block still called reset_state()
which wiped session_start on every run. Next extract then only saw records
since that reset = one message.

Locked invariants:

1. session_start (read via get_session_start_time) is preserved across a
   `divineos extract` invocation.
2. A session plan persists across mid-session extract calls.
3. clear_session_plan() and reset_state() functions still exist and work
   when called directly — only the pipeline's call site was removed.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.session_checkpoint import (
    _load_state,
    _save_state,
    get_session_start_time,
)


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    marker = Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    yield
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


@pytest.fixture
def runner():
    return CliRunner()


class TestSessionStartSurvives:
    def test_extract_preserves_session_start(self, runner):
        """The load-bearing invariant: running `divineos extract` does NOT
        reset session_start. Analyzer window stays intact."""
        runner.invoke(cli, ["init"])
        # Set a known session_start timestamp
        import time

        known_start = time.time() - 3600  # 1 hour ago
        state = _load_state()
        state["session_start"] = known_start
        _save_state(state)

        assert abs(get_session_start_time() - known_start) < 1.0

        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            result = runner.invoke(cli, ["extract"])
        assert result.exit_code == 0

        # session_start must still be the 1-hour-ago timestamp, NOT "now".
        after = get_session_start_time()
        assert abs(after - known_start) < 1.0, (
            f"reset_state wiped session_start from {known_start} to {after}"
        )

    def test_multiple_extracts_preserve_session_start(self, runner):
        """Simulates a full-session flow: set start, extract, extract again
        with --force. Start time stays stable throughout."""
        runner.invoke(cli, ["init"])
        import time

        known_start = time.time() - 7200  # 2 hours ago
        state = _load_state()
        state["session_start"] = known_start
        _save_state(state)

        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            runner.invoke(cli, ["extract"])
            assert abs(get_session_start_time() - known_start) < 1.0
            runner.invoke(cli, ["extract", "--force"])
            assert abs(get_session_start_time() - known_start) < 1.0


class TestSessionPlanSurvives:
    def test_extract_preserves_session_plan(self, runner, tmp_path, monkeypatch):
        """Session plan set during the session must survive mid-session
        extract. Previously clear_session_plan() fired in the pipeline."""
        hud_dir = tmp_path / "hud"
        hud_dir.mkdir()

        # Redirect the HUD helper to our tmp dir
        from divineos.core import _hud_io

        monkeypatch.setattr(_hud_io, "_ensure_hud_dir", lambda: hud_dir)

        # Write a fake session plan
        plan_path = hud_dir / "session_plan.json"
        plan_path.write_text('{"plan": "work on PR #161"}', encoding="utf-8")
        assert plan_path.exists()

        runner.invoke(cli, ["init"])
        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            result = runner.invoke(cli, ["extract"])
        assert result.exit_code == 0

        assert plan_path.exists(), "extract should not clear session plan"
        assert "work on PR #161" in plan_path.read_text(encoding="utf-8")
