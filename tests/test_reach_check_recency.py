"""A completed reach check must open the door it was demanded for.

2026-08-22: `divineos reach gate` printed "Reach-check clear" and `divineos
claim` was refused in the same breath. So were learn, opinion and feel — the
doorman gates all four, and every store write in this tree was unreachable.

The mechanism: ``gate_status`` answers "is a check sitting open with unread
artifacts". Zero open checks is the answer BOTH when no check was ever opened
and when one was opened and fully disposed. The doorman could not tell those
apart and blocked both, so exempting the remedy made it runnable and never
satisfiable — a wall, which the hook's own header swears it is not.

``recent_cleared_check`` is the question the doorman actually needed. These
tests pin both directions, because turning a wall into a hole is the worse
failure of the two.

Rows are written directly and every case passes an explicit ``now``, so the
answers do not depend on what this checkout's reach history happens to hold.
"""

from __future__ import annotations

import uuid

import pytest

from divineos.core import reach_check


@pytest.fixture(autouse=True)
def _tables():
    reach_check.init_reach_tables()


def _make_check(opened_at: float, items: list[str | None]) -> str:
    """One check with the given item dispositions. None means undisposed."""
    from divineos.core.knowledge import _get_connection

    check_id = f"reach-test-{uuid.uuid4().hex[:8]}"
    conn = _get_connection()
    conn.execute(
        "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?, ?, ?)",
        (check_id, f"test symptom {check_id}", opened_at),
    )
    for disposition in items:
        conn.execute(
            "INSERT INTO reach_items (item_id, check_id, artifact, origin, disposition) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                f"ri-test-{uuid.uuid4().hex[:8]}",
                check_id,
                "src/divineos/core/prior_art.py",
                "branch:test@abc123",
                disposition,
            ),
        )
    conn.commit()
    return check_id


class TestTheDoorOpens:
    def test_fully_disposed_check_in_window_is_returned(self):
        check_id = _make_check(10_000.0, [reach_check.APPLIED])
        found = reach_check.recent_cleared_check(window_seconds=600, now=10_100.0)
        assert found is not None and found.check_id == check_id

    def test_zero_item_check_counts(self):
        """open_check's own docstring: an empty result is a real outcome, and
        NOT FOUND is not the same as NOT CHECKED. A check that surfaced nothing
        is still a check that was made."""
        check_id = _make_check(20_000.0, [])
        found = reach_check.recent_cleared_check(window_seconds=600, now=20_100.0)
        assert found is not None and found.check_id == check_id

    def test_newest_cleared_check_wins(self):
        _make_check(30_000.0, [reach_check.APPLIED])
        newer = _make_check(30_200.0, [reach_check.APPLIED])
        found = reach_check.recent_cleared_check(window_seconds=600, now=30_300.0)
        assert found is not None and found.check_id == newer

    def test_a_cleared_check_is_found_past_an_open_one(self):
        """An open check blocks via gate_status, which the doorman runs first.
        This function must not additionally hide a genuine cleared check behind
        a newer open one — that would restore the wall by another route."""
        cleared = _make_check(40_000.0, [reach_check.APPLIED])
        _make_check(40_200.0, [None])
        found = reach_check.recent_cleared_check(window_seconds=600, now=40_300.0)
        assert found is not None and found.check_id == cleared


class TestTheDoorStaysShut:
    """A wall turned into a hole is the worse outcome, so each of these is a
    case where the gate must still fire."""

    def test_check_older_than_the_window(self):
        _make_check(50_000.0, [reach_check.APPLIED])
        assert reach_check.recent_cleared_check(window_seconds=60, now=90_000.0) is None

    def test_check_with_an_undisposed_item(self):
        """Opening a check and ignoring what it surfaced is the exact failure
        the mechanism exists for. It must not count as having asked."""
        _make_check(60_000.0, [reach_check.APPLIED, None])
        assert reach_check.recent_cleared_check(window_seconds=600, now=60_100.0) is None

    def test_several_half_done_checks_do_not_add_up_to_one(self):
        _make_check(70_000.0, [None])
        _make_check(70_100.0, [None])
        assert reach_check.recent_cleared_check(window_seconds=600, now=70_200.0) is None
