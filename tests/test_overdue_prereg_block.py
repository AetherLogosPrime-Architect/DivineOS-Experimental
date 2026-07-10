"""Tests for _check_overdue_prereg_block in pre_tool_use_gate.

2026-07-07 Andrew fix: pre-registration reviews used to be a briefing
surface that could be scrolled past. "No warnings.. they do not work."
The doorman now blocks non-bypass tool use until every overdue pre-reg
either records its outcome or is explicitly deferred. Paired with the
review-days default drop 30 -> 7 so overdue actually bites within the
week.
"""

from __future__ import annotations

import time

from divineos.core.pre_registrations.store import (
    Outcome,
    _get_connection,
    file_pre_registration,
    init_pre_registrations_tables,
    record_outcome,
)
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block


def _backdate_review(prereg_id: str, days_ago: float) -> None:
    """Move a pre-reg's review_ts into the past to simulate overdue.

    file_pre_registration always calls time.time() so we can't create an
    already-overdue row directly through the public API. This helper
    backdates in the DB — test-only, matches the pattern used by other
    time-sensitive tests in the suite.
    """
    ts = time.time() - days_ago * 24 * 3600
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (ts, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()


def test_no_preregs_no_block():
    """Clean slate — no pre-registrations, no block. Returns None."""
    init_pre_registrations_tables()
    assert _check_overdue_prereg_block() is None


def test_open_prereg_not_yet_overdue_does_not_block():
    """Future review date, OPEN outcome — no block."""
    init_pre_registrations_tables()
    file_pre_registration(
        mechanism="test-not-yet-due",
        claim="The mechanism will do X",
        success_criterion="Observe Y within window",
        falsifier="Observe Z during window",
        review_window_days=7,
        actor="aether",
    )
    assert _check_overdue_prereg_block() is None


def test_overdue_prereg_blocks_with_deny_message():
    """Review date in the past, OPEN outcome — block fires with a deny
    decision containing the prereg id and the recovery command."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-overdue-mechanism",
        claim="The mechanism will do X",
        success_criterion="Observe Y within window",
        falsifier="Observe Z during window",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    decision = _check_overdue_prereg_block()
    assert decision is not None
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert "OVERDUE PRE-REGISTRATIONS" in reason
    assert prereg_id[:20] in reason
    assert "divineos prereg assess" in reason


def test_recording_outcome_clears_the_block():
    """After recording a terminal outcome the pre-reg is no longer OPEN,
    so the overdue gate returns None again."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-outcome-clears",
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    assert _check_overdue_prereg_block() is not None
    record_outcome(
        prereg_id=prereg_id,
        actor="andrew",
        outcome=Outcome.SUCCESS,
        notes="Verified the mechanism held over the review window.",
    )
    assert _check_overdue_prereg_block() is None


def test_deferring_clears_the_block():
    """DEFERRED is also a terminal outcome, so it clears the block —
    matches the operator-facing recovery text in the deny message."""
    init_pre_registrations_tables()
    prereg_id = file_pre_registration(
        mechanism="test-defer-clears",
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )
    _backdate_review(prereg_id, days_ago=3)
    assert _check_overdue_prereg_block() is not None
    record_outcome(
        prereg_id=prereg_id,
        actor="andrew",
        outcome=Outcome.DEFERRED,
        notes="Need more time before I can honestly assess this outcome.",
    )
    assert _check_overdue_prereg_block() is None


def test_multiple_overdue_all_named_in_message():
    """Deny message lists overdue IDs (capped at 5 preview + more-count)
    so the operator knows exactly which pre-regs need attention."""
    init_pre_registrations_tables()
    ids = []
    for i in range(3):
        prereg_id = file_pre_registration(
            mechanism=f"multi-overdue-{i}",
            claim="X",
            success_criterion="Y",
            falsifier="Z",
            review_window_days=7,
            actor="aether",
        )
        _backdate_review(prereg_id, days_ago=3)
        ids.append(prereg_id)
    decision = _check_overdue_prereg_block()
    assert decision is not None
    reason = decision["hookSpecificOutput"]["permissionDecisionReason"]
    assert "3 pre-registration(s)" in reason
    for prereg_id in ids:
        assert prereg_id[:20] in reason
