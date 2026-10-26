"""A date alone never blocks work. Only a review that reached its count of uses may (Dad, 2026-10-21).

The date-based reviews all fell due at once, stopped work in the middle of the ritual right before compaction,
and said nothing about whether anything had been used: "if it was use based they would trigger randomly during
its last use that triggers it, and not in the middle of the ritual".

The pair is the point. "A date does not block" alone is satisfied by a gate that never blocks anything, so the
same kind of row is shown BLOCKING once it has reached its count.
"""

from _prereg_helpers import make_due_by_use, make_overdue_by_date

from divineos.core.pre_registrations.store import (
    Outcome,
    file_pre_registration,
    get_blocking_pre_registrations,
    get_overdue_pre_registrations,
    init_pre_registrations_tables,
    record_outcome,
)
from divineos.hooks.pre_tool_use_gate import _check_overdue_prereg_block

SOME_WORK = "git commit -m x"


def _fresh(label: str) -> str:
    init_pre_registrations_tables()
    return file_pre_registration(
        mechanism=label,
        claim="X",
        success_criterion="Y",
        falsifier="Z",
        review_window_days=7,
        actor="aether",
    )


def _close(*ids: str) -> None:
    for pid in ids:
        record_outcome(prereg_id=pid, actor="andrew", outcome=Outcome.SUCCESS, notes="cleanup")


def _reason(decision) -> str:
    return decision["hookSpecificOutput"]["permissionDecisionReason"]


def test_a_review_past_its_date_does_not_block_work():
    pid = _fresh("date-only-never-blocks")
    make_overdue_by_date(pid, days_ago=3)
    try:
        assert _check_overdue_prereg_block(SOME_WORK) is None
    finally:
        _close(pid)


def test_a_review_past_its_date_is_still_reported_as_overdue():
    """Informational, not hidden: the briefing keeps seeing it."""
    pid = _fresh("date-only-still-listed")
    make_overdue_by_date(pid, days_ago=3)
    try:
        assert pid in {p.prereg_id for p in get_overdue_pre_registrations()}
        assert pid not in {p.prereg_id for p in get_blocking_pre_registrations()}
    finally:
        _close(pid)


def test_the_same_review_blocks_once_it_has_reached_its_count_of_uses():
    pid = _fresh("count-reached-blocks")
    make_overdue_by_date(pid, days_ago=3)
    assert _check_overdue_prereg_block(SOME_WORK) is None  # still only a date
    make_due_by_use(pid)
    try:
        decision = _check_overdue_prereg_block(SOME_WORK)
        assert decision is not None
        assert "reached their count of uses" in _reason(decision)
    finally:
        _close(pid)


def test_dates_do_not_hide_a_review_that_reached_its_count():
    """Both kinds open at once: the date row stays quiet, the count row stops work, and only it is named."""
    by_date = _fresh("both-kinds-date")
    by_use = _fresh("both-kinds-use")
    make_overdue_by_date(by_date, days_ago=5)
    make_due_by_use(by_use)
    try:
        reason = _reason(_check_overdue_prereg_block(SOME_WORK))
        assert by_use[:20] in reason
        assert by_date[:20] not in reason
        assert "1 pre-registration(s)" in reason
    finally:
        _close(by_date, by_use)
