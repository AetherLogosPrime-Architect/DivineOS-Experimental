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

    def test_truth_file_never_stores_raw_id(self, isolated_truth):
        """Unfakeability contract (Andrew 2026-05-29): the gate-side store
        holds only a hash, never the raw ID — so catting it reveals nothing
        presentable. A future refactor that reintroduces raw-id storage must
        break this test, not slip through silently."""
        bid = briefing_id.issue_briefing_id(tool_count=0)
        truth = briefing_id._read_truth()
        assert "id" not in truth, "raw ID must never be persisted"
        assert truth.get("id_hash"), "the hash must be stored"
        assert bid not in str(truth), "the raw ID must not appear anywhere in the store"
        # 128-bit token → 32 hex chars; brute-forcing the hash is infeasible.
        assert len(bid) == 32

    def test_high_entropy_token(self, isolated_truth):
        a = briefing_id.issue_briefing_id(tool_count=0)
        b = briefing_id.issue_briefing_id(tool_count=0)
        assert a != b and len(a) == 32 and len(b) == 32


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
        # The raw ID comes from the return value (→ printed into context),
        # never from the truth file — the file holds only a hash now.
        bid = briefing_id.issue_briefing_id(tool_count=0)
        # Drift to near expiry, then a correct recall re-stamps the window.
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

    def test_propagates_exception_on_ledger_error(self, monkeypatch):
        """Fable audit Round 8 fix (2026-07-03): current_tool_count()
        propagates ledger read failures instead of fail-soft-to-0.

        Fable's finding: fail-soft-to-0 masked the failure from
        staleness_signal's outer try/except, producing a spurious
        fresh-pass with is_fresh=True on a stale briefing (negative
        delta < expiry). Propagating the exception lets the outer
        fail-closed guard correctly report stale. See PR #298.

        This test used to assert the OLD `== 0` behavior. It is
        renamed and rewritten to assert the current propagates-
        exception behavior — the Round 8 fix that the rest of the
        PR is landing.
        """

        def _boom():
            raise RuntimeError("ledger unreadable")

        # count_events is imported inside the function, so patch at source.
        import divineos.core.ledger as _ledger
        import pytest

        monkeypatch.setattr(_ledger, "count_events", _boom)
        with pytest.raises(RuntimeError, match="ledger unreadable"):
            briefing_id.current_tool_count()


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
