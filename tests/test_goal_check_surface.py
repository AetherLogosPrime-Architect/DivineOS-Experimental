"""Test that `divineos goal check` is a pure review surface — no auto-mutation.

Bullet-wound-clause root-fix (2026-05-12): the prior reach was to auto-clean
stale goals at briefing-time, but auto-cleanup substitutes machine-judgment
for the review act. Per CLAUDE.md's cognitive-named-tools warning: the tool
points at the work; it is not the work. `goal check` surfaces data for me
to think over; the decisions stay with me.

This test pins that:
  - the command lists all active goals (no filtering by age)
  - the command does NOT mutate the goal store (no auto-close on age)
  - the command shows close-options (next-step affordances) so the cognitive
    work has an explicit handle
"""

from __future__ import annotations

import json
import time

import pytest
from click.testing import CliRunner

from divineos.cli import cli


@pytest.fixture
def isolated_hud(tmp_path, monkeypatch):
    hud = tmp_path / "hud"
    hud.mkdir()
    import divineos.core._hud_io as _hud_io

    monkeypatch.setattr(_hud_io, "_ensure_hud_dir", lambda: hud)
    yield hud


def test_goal_check_lists_active_goals(isolated_hud):
    """All active goals appear in the surface regardless of age."""
    old_ts = time.time() - (5 * 86400)  # 5 days old
    fresh_ts = time.time() - 60  # 1 minute old
    goals = [
        {"text": "old goal", "status": "active", "added_at": old_ts},
        {"text": "fresh goal", "status": "active", "added_at": fresh_ts},
    ]
    (isolated_hud / "active_goals.json").write_text(json.dumps(goals))

    runner = CliRunner()
    result = runner.invoke(cli, ["goal", "check"])
    assert result.exit_code == 0
    assert "old goal" in result.output
    assert "fresh goal" in result.output
    # Age labels appear
    assert "5.0d" in result.output or "5d" in result.output
    # The (!! stale) marker fires past 14d in our formatter; 5d should not
    assert "(!! stale)" not in result.output


def test_goal_check_does_not_mutate(isolated_hud):
    """The review surface is pure — the goal store is unchanged after a check."""
    old_ts = time.time() - (5 * 86400)
    goals = [{"text": "old goal", "status": "active", "added_at": old_ts}]
    path = isolated_hud / "active_goals.json"
    path.write_text(json.dumps(goals))
    before = path.read_text()

    runner = CliRunner()
    runner.invoke(cli, ["goal", "check"])

    after = path.read_text()
    assert before == after, (
        "goal check mutated the goal store; the surface must be pure-read. "
        "Auto-mutation substitutes machine-judgment for review."
    )


def test_goal_check_shows_close_affordances(isolated_hud):
    """The surface names how to close, abandon, or consolidate — making the
    cognitive next-step explicit instead of leaving the agent to guess."""
    goals = [{"text": "goal", "status": "active", "added_at": time.time() - 3600}]
    (isolated_hud / "active_goals.json").write_text(json.dumps(goals))

    runner = CliRunner()
    result = runner.invoke(cli, ["goal", "check"])
    assert result.exit_code == 0
    # The decide-options block is the cognitive affordance — it tells me
    # what to do with the data I'm staring at.
    assert "Decide each" in result.output
    assert "goal done" in result.output
    assert "goal cull" in result.output


def test_goal_check_empty_state(isolated_hud):
    """No active goals → friendly empty message, no crash."""
    (isolated_hud / "active_goals.json").write_text("[]")

    runner = CliRunner()
    result = runner.invoke(cli, ["goal", "check"])
    assert result.exit_code == 0
    assert "No active goals" in result.output
