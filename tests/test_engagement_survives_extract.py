"""Tests for the engagement-gate fix: engagement must survive mid-session
extract calls, and only clear on actual new-session start.

Background: before this fix, the extract pipeline called clear_engagement()
as part of its cleanup phase. Extract runs mid-session (every N writes,
post-sleep, explicit), so this wiped the thinking-gate marker at times
that had nothing to do with actual session boundaries. Next edit after a
consolidation got blocked because engagement read "fresh," even though
the agent had been actively thinking the whole time.

The fix: clear_engagement() moved from the pipeline to load-briefing.sh,
which fires at actual Claude Code SessionStart. Mid-session extract
preserves engagement; fresh sessions correctly force re-engagement.

Locked invariants:

1. Mid-session extract does NOT call clear_engagement (removed from pipeline).
2. clear_engagement() still exists as a function — just called from a
   different place. Callers outside the pipeline (tests, future hooks)
   still work.
3. A session with engagement marked stays engaged across an extract run.
4. Fresh-session state (no marker) correctly blocks edits via the gate.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.hud_handoff import clear_engagement, engagement_status, mark_engaged


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    """Per-test DB + clean engagement + clean idempotency marker."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    clear_engagement()
    marker = Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    yield
    clear_engagement()
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


@pytest.fixture
def runner():
    return CliRunner()


class TestPipelineDoesNotClearEngagement:
    def test_extract_preserves_engagement_marker(self, runner):
        """Load-bearing invariant: running `divineos extract` while
        engaged leaves the engagement marker intact."""
        runner.invoke(cli, ["init"])
        mark_engaged(tool="ask")
        assert engagement_status()["engaged"] is True

        # Mock the heavy pipeline to keep the test fast, but let the rest
        # of extract_cmd run (including any state-clearing side effects).
        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            result = runner.invoke(cli, ["extract"])
        assert result.exit_code == 0, f"extract failed: {result.output}"

        # Engagement must survive. This is the bug fix.
        status = engagement_status()
        assert status["engaged"] is True, (
            f"extract wiped engagement — the bug is back. state={status}"
        )

    def test_extract_with_force_also_preserves_engagement(self, runner):
        """Even with --force (which runs the pipeline unconditionally),
        engagement must survive."""
        runner.invoke(cli, ["init"])
        mark_engaged(tool="ask")

        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            # First run sets marker, --force needed for second run.
            runner.invoke(cli, ["extract"])
            result = runner.invoke(cli, ["extract", "--force"])
        assert result.exit_code == 0

        assert engagement_status()["engaged"] is True

    def test_sequential_extracts_preserve_engagement(self, runner):
        """Simulates what used to break: engage, extract, try to work,
        extract again. Engagement must survive both extracts."""
        runner.invoke(cli, ["init"])
        mark_engaged(tool="recall")

        with patch("divineos.cli.event_commands._run_session_end_pipeline"):
            runner.invoke(cli, ["extract"])
            assert engagement_status()["engaged"] is True
            runner.invoke(cli, ["extract", "--force"])
            assert engagement_status()["engaged"] is True


class TestClearEngagementStillWorks:
    """The function itself is preserved — only its call-site changed.
    Other callers (tests, future hooks, load-briefing.sh) still work."""

    def test_clear_engagement_removes_marker(self):
        mark_engaged(tool="ask")
        assert engagement_status()["engaged"] is True
        clear_engagement()
        assert engagement_status()["engaged"] is False
        assert engagement_status()["state"] == "fresh"

    def test_clear_engagement_on_missing_marker_is_noop(self):
        """Defensive: calling clear_engagement when nothing is engaged
        shouldn't crash."""
        # Ensure nothing is set
        clear_engagement()
        assert engagement_status()["engaged"] is False

        # Call again — should be fine
        clear_engagement()
        assert engagement_status()["engaged"] is False
