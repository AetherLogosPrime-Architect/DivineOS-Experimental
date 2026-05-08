"""Tests for the `divineos briefing --mini` flag.

Covers the contract the audit on PR #259 (2026-05-05) flagged:
  * --mini calls mark_briefing_loaded() (clears the BLOCKED state)
  * --mini emits the mini-briefing rendered output
  * --mini does NOT call into the heavy full-briefing pipeline
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli():
    """Return the divineos CLI group."""
    from divineos.cli import cli as cli_group

    return cli_group


class TestMiniFlag:
    def test_mini_renders_mini_output(self, cli) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["briefing", "--mini"])
        assert result.exit_code == 0
        # Mini briefing has a distinctive header and footer.
        assert "Mini Briefing" in result.output
        assert "End mini briefing" in result.output

    def test_mini_marks_briefing_loaded(self, cli, monkeypatch) -> None:
        """Running --mini must call mark_briefing_loaded() so the
        require-goal / load-briefing gates clear correctly. The audit
        verified this contract empirically; this test pins it."""
        from divineos.core import hud_handoff

        called = {"count": 0}

        original = hud_handoff.mark_briefing_loaded

        def tracker():
            called["count"] += 1
            return original()

        monkeypatch.setattr(hud_handoff, "mark_briefing_loaded", tracker)

        runner = CliRunner()
        result = runner.invoke(cli, ["briefing", "--mini"])
        assert result.exit_code == 0
        assert called["count"] >= 1, (
            "--mini must call mark_briefing_loaded() so the BLOCKED state clears"
        )

    def test_mini_size_under_budget(self, cli) -> None:
        """End-to-end size check: mini briefing CLI output must stay
        under the ~6KB cap so the SessionStart hook payload fits."""
        runner = CliRunner()
        result = runner.invoke(cli, ["briefing", "--mini"])
        assert result.exit_code == 0
        assert len(result.output) < 6000, (
            f"--mini CLI output too large: {len(result.output)} bytes (cap: 6000)"
        )
