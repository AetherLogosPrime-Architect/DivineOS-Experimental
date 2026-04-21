"""Tests for watchmen.drift_state — data-as-metric replacement for cadence gate.

Commit C of the tiered-audit redesign. Replaced the wall-clock cadence gate
(removed 2026-04-21) with an operations-based informational surface.
Per council consultation consult-2760777ef7a3 → round-96a6858fb5e6 (MEDIUM):

  * Jacobs: don't replace the informal loop with an elaborate metric
  * Dijkstra: prefer clarity (plain counts) over cleverness (weighted sums)
  * Beer: match the metric's variety to the state's variety
  * Kahneman: slow down — start with 4 dimensions, grow with evidence
"""

from __future__ import annotations

import time

import pytest

from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.drift_state import (
    compute_drift_state,
    format_for_briefing,
    last_medium_plus_audit_ts,
    last_strong_audit_ts,
)
from divineos.core.watchmen.store import submit_finding, submit_round


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    """Isolate each test on its own DB file."""
    db = tmp_path / "drift.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db))
    from divineos.core.ledger import init_db

    init_db()
    init_watchmen_tables()
    yield db


def _log_event(event_type: str, actor: str, payload: dict) -> str:
    """Helper: write a system_events row via the real log_event API."""
    from divineos.core.ledger import log_event

    return log_event(event_type, actor, payload, validate=False)


class TestLastAuditTimestamps:
    def test_no_audits_returns_none(self, tmp_db):
        assert last_medium_plus_audit_ts() is None
        assert last_strong_audit_ts() is None

    def test_weak_round_does_not_reset_medium_counter(self, tmp_db):
        submit_round(actor="user", focus="weak")  # defaults to WEAK
        assert last_medium_plus_audit_ts() is None
        assert last_strong_audit_ts() is None

    def test_council_round_sets_medium_ts(self, tmp_db):
        submit_round(actor="council", focus="medium")  # defaults to MEDIUM
        assert last_medium_plus_audit_ts() is not None
        assert last_strong_audit_ts() is None

    def test_grok_round_sets_both_ts(self, tmp_db):
        submit_round(actor="grok", focus="strong")  # defaults to STRONG
        assert last_medium_plus_audit_ts() is not None
        assert last_strong_audit_ts() is not None

    def test_most_recent_wins(self, tmp_db):
        r1 = submit_round(actor="council", focus="first")
        time.sleep(0.01)
        r2 = submit_round(actor="council", focus="second")
        latest = last_medium_plus_audit_ts()
        from divineos.core.watchmen.store import get_round

        assert latest == get_round(r2).created_at
        assert latest > get_round(r1).created_at


class TestComputeDriftState:
    def test_fresh_db_has_zero_drift(self, tmp_db):
        state = compute_drift_state()
        assert state.turns_since_medium == 0
        assert state.code_actions_since_medium == 0
        assert state.rounds_filed_since_medium == 0
        assert state.open_findings_above_low == 0
        assert state.last_medium_audit_ts is None
        assert state.last_strong_audit_ts is None

    def test_user_input_increments_turn_counter(self, tmp_db):
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "hi",
                "timestamp": "2026-04-21T10:00:00",
                "session_id": "abc",
            },
        )
        state = compute_drift_state()
        assert state.turns_since_medium == 1

    def test_tool_call_for_edit_counts_as_code_action(self, tmp_db):
        _log_event(
            "TOOL_CALL",
            "assistant",
            {
                "tool_name": "Edit",
                "args": {"file_path": "x.py"},
                "timestamp": "2026-04-21T10:00:00",
                "session_id": "abc",
            },
        )
        state = compute_drift_state()
        assert state.code_actions_since_medium == 1

    def test_tool_call_for_unrelated_tool_does_not_count(self, tmp_db):
        _log_event(
            "TOOL_CALL",
            "assistant",
            {
                "tool_name": "Bash",
                "args": {"command": "ls"},
                "timestamp": "2026-04-21T10:00:00",
                "session_id": "abc",
            },
        )
        state = compute_drift_state()
        assert state.code_actions_since_medium == 0

    def test_medium_audit_resets_both_counters(self, tmp_db):
        """After a MEDIUM audit, subsequent events count from zero."""
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "before audit",
                "timestamp": "2026-04-21T10:00:00",
                "session_id": "abc",
            },
        )
        _log_event(
            "TOOL_CALL",
            "assistant",
            {
                "tool_name": "Write",
                "args": {},
                "timestamp": "t",
                "session_id": "abc",
            },
        )
        # Now file a MEDIUM audit
        time.sleep(0.01)
        submit_round(actor="council", focus="reset point")
        time.sleep(0.01)
        # Events AFTER the audit
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "after audit",
                "timestamp": "2026-04-21T10:01:00",
                "session_id": "abc",
            },
        )
        state = compute_drift_state()
        assert state.turns_since_medium == 1  # only the post-audit turn
        assert state.code_actions_since_medium == 0  # the pre-audit Write is excluded

    def test_weak_audit_does_not_reset_counter(self, tmp_db):
        """WEAK-tier rounds do not reset the MEDIUM+ counter."""
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "t1",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        time.sleep(0.01)
        submit_round(actor="user", focus="weak round")  # WEAK
        time.sleep(0.01)
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "t2",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        state = compute_drift_state()
        # Both turns still counted because WEAK audits don't reset
        assert state.turns_since_medium == 2

    def test_rounds_filed_counter_tracks_weak_rounds_since_medium(self, tmp_db):
        """After a MEDIUM audit, WEAK rounds filed accumulate as unvalidated observations."""
        submit_round(actor="council", focus="medium baseline")
        time.sleep(0.01)
        submit_round(actor="user", focus="weak 1")
        submit_round(actor="user", focus="weak 2")
        state = compute_drift_state()
        assert state.rounds_filed_since_medium == 2

    def test_open_high_finding_counts(self, tmp_db):
        rid = submit_round(actor="council", focus="f")
        submit_finding(
            round_id=rid,
            actor="council",
            severity="HIGH",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        state = compute_drift_state()
        assert state.open_findings_above_low == 1

    def test_low_finding_does_not_count(self, tmp_db):
        rid = submit_round(actor="council", focus="f")
        submit_finding(
            round_id=rid,
            actor="council",
            severity="LOW",
            category="BEHAVIOR",
            title="t",
            description="d",
        )
        state = compute_drift_state()
        assert state.open_findings_above_low == 0


class TestBriefingFormatter:
    def test_empty_state_returns_empty_string(self, tmp_db):
        assert format_for_briefing() == ""

    def test_with_activity_surfaces_block(self, tmp_db):
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "hello",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert out
        assert "[drift state]" in out

    def test_names_no_medium_audit_when_none_filed(self, tmp_db):
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert "no MEDIUM+ audit has ever been filed" in out

    def test_names_since_last_medium_when_filed(self, tmp_db):
        submit_round(actor="council", focus="ref")
        time.sleep(0.01)
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert "since last MEDIUM+ audit round" in out

    def test_surfaces_no_strong_warning_when_never_filed(self, tmp_db):
        submit_round(actor="council", focus="medium only")
        time.sleep(0.01)
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert "no STRONG audit on record" in out

    def test_does_not_surface_no_strong_when_strong_exists(self, tmp_db):
        submit_round(actor="grok", focus="strong")
        time.sleep(0.01)
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert "no STRONG audit on record" not in out

    def test_includes_each_dimension_line(self, tmp_db):
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        assert "turns" in out
        assert "code actions" in out
        assert "audit rounds filed" in out
        assert "open findings" in out

    def test_includes_action_hint(self, tmp_db):
        _log_event(
            "USER_INPUT",
            "user",
            {
                "content": "x",
                "timestamp": "t",
                "session_id": "s",
            },
        )
        out = format_for_briefing()
        # The block must point at the operator actions that clear/address drift
        assert "council" in out.lower() or "audit" in out.lower()


class TestCadenceModuleDeleted:
    """Commit C deletes the old cadence module. Catch any stale imports."""

    def test_cadence_module_is_gone(self):
        with pytest.raises(ImportError):
            from divineos.core.watchmen import cadence  # noqa: F401

    def test_watchmen_package_no_longer_exports_cadence(self):
        from divineos.core import watchmen

        assert not hasattr(watchmen, "CADENCE_THRESHOLD_DAYS")
        assert not hasattr(watchmen, "is_overdue")
        assert not hasattr(watchmen, "format_cadence_warning")
