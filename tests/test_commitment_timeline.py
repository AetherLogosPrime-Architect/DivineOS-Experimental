"""Tests for the unified commitment-collapse timeline.

Realizes Pillar VI's `commitment_collapse_event` pull (omni_mantra_walk/07):
filing-claim / decision / commitment / pre-reg / goal as a unified
collapse-event-type. DivineOS has each as its own store; the timeline
command surfaces them as one stream sorted by timestamp.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Each test runs against a fresh DB so timeline rows are predictable."""
    db_path = tmp_path / "timeline_test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    from divineos.core.ledger import init_db

    init_db()
    yield db_path
    os.environ.pop("DIVINEOS_DB", None)


@pytest.fixture
def cli():
    from divineos.cli import cli as cli_group

    return cli_group


class TestCommitmentTimeline:
    def test_timeline_command_exists(self, cli):
        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--help"])
        assert result.exit_code == 0
        assert "Unified commitment-collapse timeline" in result.output

    def test_timeline_returns_no_commitments_when_empty(self, cli):
        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--days", "1"])
        assert result.exit_code == 0
        assert "No commitments" in result.output

    def test_timeline_surfaces_decisions(self, cli):
        from divineos.core.decision_journal import init_decision_journal, record_decision

        init_decision_journal()
        record_decision(
            content="test decision for timeline",
            reasoning="needed for unified timeline test",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--days", "1"])
        assert result.exit_code == 0
        assert "[DECIDE]" in result.output
        assert "test decision for timeline" in result.output

    def test_timeline_surfaces_goals(self, cli):
        from divineos.core.hud_state import add_goal

        add_goal("test goal for timeline")

        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--days", "1"])
        assert result.exit_code == 0
        assert "[GOAL" in result.output
        assert "test goal for timeline" in result.output

    def test_timeline_unified_across_types(self, cli):
        """The whole point: multiple types appear in one stream."""
        from divineos.core.decision_journal import init_decision_journal, record_decision
        from divineos.core.hud_state import add_goal

        init_decision_journal()
        record_decision(content="decision-A", reasoning="r")
        add_goal("goal-A")

        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--days", "1"])
        assert result.exit_code == 0
        # Both type-tags must appear in the same output
        assert "[DECIDE]" in result.output
        assert "[GOAL" in result.output

    def test_timeline_filters_by_days(self, cli):
        """The --days flag should limit the lookback window. Days=0
        means cutoff is now — even just-added items are at-or-before
        cutoff, so they should fail the >=cutoff check."""
        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--days", "0"])
        assert result.exit_code == 0
        # 0-day window with empty DB → "No commitments"
        assert "No commitments" in result.output

    def test_timeline_documents_known_limitations(self, cli):
        """Per substrate-query (knowledge 5f502a1a, pre-reg portability):
        the timeline reads runtime-DB-only data; same portability concern.
        The docstring should name this so it's not silently inherited."""
        runner = CliRunner()
        result = runner.invoke(cli, ["commitment", "timeline", "--help"])
        assert result.exit_code == 0
        assert "Known limitations" in result.output
        assert "runtime-DB-only" in result.output or "runtime-DB" in result.output
