"""Tests for the pre-registrations module.

Pre-registrations are the Goodhart-prevention substrate: every new detector
ships with a written prediction, a specific falsifier, and a ledger-scheduled
review. The tests below lock in the invariants that make that guarantee real:

* An empty falsifier / success criterion / claim is rejected at file time.
* Zero or negative review windows are rejected.
* Internal actors (the running agent, pipelines, hooks) cannot record
  outcomes — only external actors can.
* Outcomes are one-way. Once recorded, they cannot be rewritten.
* OPEN is not a valid recorded outcome — only terminal states close the loop.
* Overdue detection uses review_ts < now AND outcome == OPEN.
"""

import os
import time

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.pre_registrations import (
    Outcome,
    PreRegistration,
    count_by_outcome,
    file_pre_registration,
    format_overdue_warning,
    format_summary,
    get_overdue_pre_registrations,
    get_pre_registration,
    init_pre_registrations_tables,
    list_pre_registrations,
    record_outcome,
)


@pytest.fixture(autouse=True)
def _prereg_db(tmp_path):
    """Fresh DB per test."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_pre_registrations_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── Filing invariants ────────────────────────────────────────────────


class TestFileInvariants:
    def test_basic_file_succeeds(self):
        pid = file_pre_registration(
            actor="aether",
            mechanism="test_mechanism",
            claim="detects X correctly",
            success_criterion="metric Y drops in 30 days",
            falsifier="metric Y unchanged after 30 days of data",
            review_window_days=30,
        )
        assert pid.startswith("prereg-")
        p = get_pre_registration(pid)
        assert isinstance(p, PreRegistration)
        assert p.mechanism == "test_mechanism"
        assert p.outcome == Outcome.OPEN

    def test_empty_mechanism_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            file_pre_registration(
                actor="a",
                mechanism="",
                claim="c",
                success_criterion="s",
                falsifier="f",
            )

    def test_empty_claim_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            file_pre_registration(
                actor="a",
                mechanism="m",
                claim="   ",
                success_criterion="s",
                falsifier="f",
            )

    def test_empty_falsifier_rejected(self):
        """Popper's rule: no falsifier = not a prediction."""
        with pytest.raises(ValueError, match="cannot be empty"):
            file_pre_registration(
                actor="a",
                mechanism="m",
                claim="c",
                success_criterion="s",
                falsifier="",
            )

    def test_empty_success_criterion_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            file_pre_registration(
                actor="a",
                mechanism="m",
                claim="c",
                success_criterion="",
                falsifier="f",
            )

    def test_empty_actor_rejected(self):
        with pytest.raises(ValueError, match="Actor name cannot be empty"):
            file_pre_registration(
                actor="   ",
                mechanism="m",
                claim="c",
                success_criterion="s",
                falsifier="f",
            )

    def test_zero_review_window_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            file_pre_registration(
                actor="a",
                mechanism="m",
                claim="c",
                success_criterion="s",
                falsifier="f",
                review_window_days=0,
            )

    def test_negative_review_window_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            file_pre_registration(
                actor="a",
                mechanism="m",
                claim="c",
                success_criterion="s",
                falsifier="f",
                review_window_days=-1,
            )

    def test_actor_is_normalized(self):
        pid = file_pre_registration(
            actor="  Aether  ",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        p = get_pre_registration(pid)
        assert p.actor == "aether"

    def test_review_ts_is_scheduled(self):
        before = time.time()
        pid = file_pre_registration(
            actor="a",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=14,
        )
        after = time.time()
        p = get_pre_registration(pid)
        expected_min = before + 14 * 86400
        expected_max = after + 14 * 86400
        assert expected_min <= p.review_ts <= expected_max


# ── Outcome recording ────────────────────────────────────────────────


class TestOutcomeRecording:
    def _file_one(self):
        return file_pre_registration(
            actor="aether",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )

    def test_external_actor_can_record_success(self):
        pid = self._file_one()
        assert record_outcome(pid, actor="grok", outcome=Outcome.SUCCESS) is True
        p = get_pre_registration(pid)
        assert p.outcome == Outcome.SUCCESS

    def test_external_actor_can_record_failed(self):
        pid = self._file_one()
        assert record_outcome(
            pid, actor="grok", outcome=Outcome.FAILED, notes="falsifier triggered"
        )
        p = get_pre_registration(pid)
        assert p.outcome == Outcome.FAILED
        assert p.outcome_notes == "falsifier triggered"
        assert p.outcome_ts is not None

    def test_internal_actor_rejected(self):
        """The agent cannot record outcomes for its own pre-registrations —
        that would re-create the designer-user-judge collapse this mechanism
        exists to prevent."""
        pid = self._file_one()
        for internal in ("claude", "system", "pipeline", "assistant", "hook"):
            with pytest.raises(ValueError, match="internal component"):
                record_outcome(pid, actor=internal, outcome=Outcome.SUCCESS)
        # Still OPEN after all attempts
        assert get_pre_registration(pid).outcome == Outcome.OPEN

    def test_bare_claude_rejected_as_internal(self):
        """Companion to the Watchmen 'claude' fix. The bare name must never
        be accepted here either."""
        pid = self._file_one()
        with pytest.raises(ValueError, match="internal component"):
            record_outcome(pid, actor="claude", outcome=Outcome.SUCCESS)
        with pytest.raises(ValueError, match="internal component"):
            record_outcome(pid, actor="Claude", outcome=Outcome.SUCCESS)

    def test_disambiguated_claude_still_allowed(self):
        pid = self._file_one()
        assert record_outcome(pid, actor="claude-opus-auditor", outcome=Outcome.SUCCESS)

    def test_outcome_is_one_way(self):
        """Once a terminal outcome is recorded, it cannot be rewritten."""
        pid = self._file_one()
        record_outcome(pid, actor="grok", outcome=Outcome.FAILED)
        with pytest.raises(ValueError, match="already has terminal outcome"):
            record_outcome(pid, actor="grok", outcome=Outcome.SUCCESS)

    def test_cannot_record_open_outcome(self):
        """OPEN is not terminal — recording it makes no sense."""
        pid = self._file_one()
        with pytest.raises(ValueError, match="only terminal outcomes"):
            record_outcome(pid, actor="grok", outcome=Outcome.OPEN)

    def test_record_nonexistent_returns_false(self):
        assert record_outcome("prereg-doesnotexist", actor="grok", outcome=Outcome.SUCCESS) is False


# ── Overdue detection ────────────────────────────────────────────────


class TestOverdueDetection:
    def test_not_overdue_when_review_ts_in_future(self):
        file_pre_registration(
            actor="a",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        assert get_overdue_pre_registrations() == []

    def test_overdue_when_review_ts_in_past_and_open(self, tmp_path):
        pid = file_pre_registration(
            actor="a",
            mechanism="overdue_test",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=30,
        )
        # Simulate 31 days later via explicit now parameter
        future = time.time() + 31 * 86400
        overdue = get_overdue_pre_registrations(now=future)
        assert len(overdue) == 1
        assert overdue[0].prereg_id == pid

    def test_not_overdue_once_outcome_recorded(self):
        pid = file_pre_registration(
            actor="a",
            mechanism="resolved_test",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=1,
        )
        record_outcome(pid, actor="grok", outcome=Outcome.SUCCESS)
        future = time.time() + 31 * 86400
        overdue = get_overdue_pre_registrations(now=future)
        assert overdue == []  # outcome recorded -> no longer overdue

    def test_overdue_ordered_oldest_first(self):
        pid_new = file_pre_registration(
            actor="a",
            mechanism="newer",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=1,
        )
        # Manually backdate created_at and review_ts of a second one so it
        # appears "older"
        from divineos.core.knowledge import _get_connection

        pid_old = file_pre_registration(
            actor="a",
            mechanism="older",
            claim="c",
            success_criterion="s",
            falsifier="f",
            review_window_days=1,
        )
        conn = _get_connection()
        try:
            past = time.time() - 10 * 86400
            conn.execute(
                "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
                (past, pid_old),
            )
            conn.commit()
        finally:
            conn.close()

        future = time.time() + 2 * 86400
        overdue = get_overdue_pre_registrations(now=future)
        assert [o.prereg_id for o in overdue] == [pid_old, pid_new]


# ── Listing and counting ─────────────────────────────────────────────


class TestListingAndCounting:
    def test_list_filter_by_outcome(self):
        pid_a = file_pre_registration(
            actor="a",
            mechanism="m1",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        file_pre_registration(
            actor="a",
            mechanism="m2",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        record_outcome(pid_a, actor="grok", outcome=Outcome.SUCCESS)

        succ = list_pre_registrations(outcome=Outcome.SUCCESS)
        opens = list_pre_registrations(outcome=Outcome.OPEN)
        assert len(succ) == 1
        assert len(opens) == 1
        assert succ[0].prereg_id == pid_a

    def test_list_filter_by_mechanism(self):
        file_pre_registration(
            actor="a",
            mechanism="alpha_detector",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        file_pre_registration(
            actor="a",
            mechanism="beta_detector",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        alpha = list_pre_registrations(mechanism="alpha_detector")
        assert len(alpha) == 1
        assert alpha[0].mechanism == "alpha_detector"

    def test_count_by_outcome(self):
        assert count_by_outcome() == {
            "OPEN": 0,
            "SUCCESS": 0,
            "FAILED": 0,
            "INCONCLUSIVE": 0,
            "DEFERRED": 0,
        }
        p1 = file_pre_registration(
            actor="a",
            mechanism="m1",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        p2 = file_pre_registration(
            actor="a",
            mechanism="m2",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        file_pre_registration(
            actor="a",
            mechanism="m3",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        record_outcome(p1, actor="grok", outcome=Outcome.SUCCESS)
        record_outcome(p2, actor="grok", outcome=Outcome.FAILED)
        counts = count_by_outcome()
        assert counts["SUCCESS"] == 1
        assert counts["FAILED"] == 1
        assert counts["OPEN"] == 1


# ── Formatting ───────────────────────────────────────────────────────


class TestFormatting:
    def test_overdue_warning_empty_when_none(self):
        assert format_overdue_warning() == ""

    def test_summary_includes_zero_filed_hint(self):
        out = format_summary()
        assert "No pre-registrations filed yet" in out

    def test_summary_shows_counts_after_filing(self):
        file_pre_registration(
            actor="a",
            mechanism="m",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        out = format_summary()
        assert "Total:      1" in out
        assert "Open:       1" in out


# ── Ledger integration ───────────────────────────────────────────────


class TestLedgerIntegration:
    def test_filing_emits_ledger_event(self, capsys):
        from divineos.core.ledger import get_events

        pid = file_pre_registration(
            actor="aether",
            mechanism="ledger_test",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        events = get_events(event_type="PRE_REGISTRATION_FILED", limit=10)
        matched = [e for e in events if pid in str(e)]
        assert matched, f"No ledger event for filing {pid}"

    def test_outcome_emits_ledger_event(self):
        from divineos.core.ledger import get_events

        pid = file_pre_registration(
            actor="aether",
            mechanism="ledger_out_test",
            claim="c",
            success_criterion="s",
            falsifier="f",
        )
        record_outcome(pid, actor="grok", outcome=Outcome.FAILED, notes="test")
        events = get_events(event_type="PRE_REGISTRATION_OUTCOME", limit=10)
        matched = [e for e in events if pid in str(e)]
        assert matched, f"No ledger outcome event for {pid}"
