"""Tests for briefing_id — context-recall freshness token (prereg-e536aaec6144)."""

from __future__ import annotations

import pytest

from divineos.core import briefing_id


@pytest.fixture
def isolated_truth(tmp_path, monkeypatch):
    """Redirect the gate-side truth store to a tmp HUD dir."""
    monkeypatch.setattr(briefing_id, "_truth_path", lambda: tmp_path / ".briefing_id")
    return tmp_path


class TestIssueAndVerify:
    def test_correct_recall_verifies(self, isolated_truth):
        bid = briefing_id.issue_briefing_id(tool_count=0)
        ok, msg = briefing_id.verify_briefing_id(bid, current_tool_count=3)
        assert ok is True
        assert "verified" in msg.lower()

    def test_wrong_id_rejected(self, isolated_truth):
        briefing_id.issue_briefing_id(tool_count=0)
        ok, msg = briefing_id.verify_briefing_id("deadbeef", current_tool_count=1)
        assert ok is False
        assert "stale" in msg.lower() or "does not match" in msg.lower()

    def test_verify_when_none_issued(self, isolated_truth):
        ok, msg = briefing_id.verify_briefing_id("anything", current_tool_count=1)
        assert ok is False
        assert "no briefing-id" in msg.lower()

    def test_case_and_whitespace_insensitive(self, isolated_truth):
        bid = briefing_id.issue_briefing_id(tool_count=0)
        ok, _ = briefing_id.verify_briefing_id(f"  {bid.upper()}  ", current_tool_count=1)
        assert ok is True


class TestFreshness:
    def test_fresh_right_after_issue(self, isolated_truth):
        briefing_id.issue_briefing_id(tool_count=10)
        assert briefing_id.is_fresh(current_tool_count=10) is True

    def test_stale_after_expiry(self, isolated_truth):
        briefing_id.issue_briefing_id(tool_count=0)
        assert (
            briefing_id.is_fresh(current_tool_count=briefing_id.DEFAULT_EXPIRY_TOOLS + 1) is False
        )

    def test_stale_when_none_issued(self, isolated_truth):
        assert briefing_id.is_fresh(current_tool_count=0) is False

    def test_verify_restamps_freshness(self, isolated_truth):
        briefing_id.issue_briefing_id(tool_count=0)
        # Drift to near expiry, then a correct recall re-stamps the window.
        bid = briefing_id._read_truth()["id"]
        near = briefing_id.DEFAULT_EXPIRY_TOOLS - 1
        assert briefing_id.is_fresh(current_tool_count=near) is True
        briefing_id.verify_briefing_id(bid, current_tool_count=near)
        # Now fresh for another full window measured from `near`.
        assert (
            briefing_id.is_fresh(current_tool_count=near + briefing_id.DEFAULT_EXPIRY_TOOLS - 1)
            is True
        )
        assert (
            briefing_id.is_fresh(current_tool_count=near + briefing_id.DEFAULT_EXPIRY_TOOLS + 1)
            is False
        )


class TestChallengeMessage:
    def test_names_the_verify_command(self, isolated_truth):
        msg = briefing_id.challenge_message(current_tool_count=30)
        assert "briefing-id" in msg.lower()
        assert "do not look it up" in msg.lower() or "do NOT look it up" in msg


class TestCurrentToolCount:
    def test_returns_non_negative_int(self):
        n = briefing_id.current_tool_count()
        assert isinstance(n, int)
        assert n >= 0

    def test_fail_soft_to_zero_on_ledger_error(self, monkeypatch):
        def _boom():
            raise RuntimeError("ledger unreadable")

        # count_events is imported inside the function, so patch at source.
        import divineos.core.ledger as _ledger

        monkeypatch.setattr(_ledger, "count_events", _boom)
        assert briefing_id.current_tool_count() == 0


class TestCliRoundtrip:
    def test_issue_then_verify_via_cli(self, isolated_truth, monkeypatch):
        from click.testing import CliRunner
        from divineos.cli import knowledge_commands

        monkeypatch.setattr(briefing_id, "current_tool_count", lambda: 0)
        cli = __import__("click").Group()
        knowledge_commands.register(cli)
        runner = CliRunner()

        line = knowledge_commands._issue_briefing_id_line()
        bid = line.split("BRIEFING-ID:")[1].split("===")[0].strip()

        ok = runner.invoke(cli, ["briefing-id", bid])
        assert ok.exit_code == 0
        assert "[ok]" in ok.output

        bad = runner.invoke(cli, ["briefing-id", "deadbeef"])
        assert bad.exit_code == 0
        assert "[stale]" in bad.output
