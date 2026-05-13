"""Regression-pin tests for anti_slop staleness surface (Aletheia
round-ba785844a791 Finding 12 + family-audit round-6a70dcf9ec77).

The bug-shape: anti_slop was built-and-tested but not auto-scheduled.
The discipline lived in code (run_all_checks() works correctly) but
operated only when the operator manually invoked it. Without a
visibility surface, the manual-only state was silent.

This fix doesn't auto-schedule anti_slop directly (that requires
external infrastructure: system cron, scheduled-tasks daemon, or
similar). Instead, it surfaces the staleness in the briefing
dashboard so 'anti-slop hasn't run in N hours' becomes a routine
visible item — same pattern as drift_state and gate_failures rows.

These tests pin the staleness behavior so a future refactor cannot
silently drop the surface.
"""

from __future__ import annotations

import time

from divineos.core.scheduled_run import (
    EVENT_SCHEDULED_RUN_END,
    anti_slop_staleness,
)


def _emit_scheduled_end(command: str, ts: float, clean: bool, failures: list[str]) -> None:
    """Emit a SCHEDULED_RUN_END event with the given fields, then
    backdate its timestamp via direct UPDATE because log_event sets
    timestamp from time.time() inside its lock."""
    from divineos.core.ledger import get_connection, log_event

    event_id = log_event(
        EVENT_SCHEDULED_RUN_END,
        actor="test:scheduler",
        payload={
            "command": command,
            "duration_sec": 0.1,
            "clean": clean,
            "failures": failures,
            "notes": [],
        },
        validate=False,
    )
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE system_events SET timestamp = ? WHERE event_id = ?",
            (ts, event_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_never_run_is_stale() -> None:
    """LOAD-BEARING: if anti-slop has never run, the staleness surface
    must report is_stale=True. Without this, the briefing wouldn't
    surface the manual-only state to a fresh install."""
    state = anti_slop_staleness()
    assert state["is_stale"] is True
    assert state["last_run_ts"] is None
    assert state["age_seconds"] is None
    assert state["last_clean"] is None


def test_recent_clean_run_is_not_stale() -> None:
    """A clean anti-slop run within 24h: not stale, last_clean=True."""
    _emit_scheduled_end("anti-slop", time.time() - 100, clean=True, failures=[])
    state = anti_slop_staleness()
    assert state["is_stale"] is False
    assert state["last_clean"] is True
    assert state["last_failures"] == []
    assert state["age_seconds"] is not None
    assert state["age_seconds"] < 24 * 3600


def test_old_clean_run_is_stale() -> None:
    """A clean anti-slop run > 24h ago: stale, last_clean=True. The
    discipline is to run anti-slop daily; surface the gap."""
    _emit_scheduled_end("anti-slop", time.time() - 25 * 3600, clean=True, failures=[])
    state = anti_slop_staleness()
    assert state["is_stale"] is True
    assert state["last_clean"] is True


def test_recent_failed_run_surfaces_failures() -> None:
    """A failed anti-slop run within 24h: not stale (it ran recently),
    but last_clean=False and failures populated. Briefing surface
    distinguishes 'stale' from 'failed'."""
    failures = ["sycophancy_detector did not fire on known-bad input"]
    _emit_scheduled_end("anti-slop", time.time() - 100, clean=False, failures=failures)
    state = anti_slop_staleness()
    assert state["is_stale"] is False
    assert state["last_clean"] is False
    assert state["last_failures"] == failures


def test_only_anti_slop_runs_counted() -> None:
    """Other scheduled commands (health, verify, etc.) don't affect
    the anti-slop staleness measurement. If they did, running 'health'
    daily would mask an anti-slop gap."""
    # A health run an hour ago — should NOT make anti-slop fresh.
    _emit_scheduled_end("health", time.time() - 3600, clean=True, failures=[])
    state = anti_slop_staleness()
    assert state["is_stale"] is True
    assert state["last_run_ts"] is None  # no anti-slop run found


def test_most_recent_anti_slop_run_wins() -> None:
    """When multiple anti-slop runs exist, staleness reflects the
    MOST RECENT one. An older clean run does not mask a recent failed
    run."""
    # Old clean run (25h ago)
    _emit_scheduled_end("anti-slop", time.time() - 25 * 3600, clean=True, failures=[])
    # Recent failed run (1h ago)
    failures = ["theater_monitor regression"]
    _emit_scheduled_end("anti-slop", time.time() - 3600, clean=False, failures=failures)
    state = anti_slop_staleness()
    assert state["is_stale"] is False  # ran 1h ago, not stale
    assert state["last_clean"] is False  # most recent was failed
    assert state["last_failures"] == failures


def test_dashboard_row_surfaces_staleness() -> None:
    """Integration test: the dashboard row appears when stale or
    failed, and is hidden when fresh+clean."""
    from divineos.core.briefing_dashboard import _row_anti_slop_staleness

    # Never-run state surfaces a row
    row = _row_anti_slop_staleness()
    assert row is not None
    assert row.area == "Anti-slop"
    assert row.stale_count == 1
    assert "never run" in row.detail.lower() or "since" in row.detail.lower()

    # Fresh+clean state hides the row (no surface needed)
    _emit_scheduled_end("anti-slop", time.time() - 60, clean=True, failures=[])
    row = _row_anti_slop_staleness()
    assert row is None, "Fresh+clean anti-slop should NOT surface a row"
