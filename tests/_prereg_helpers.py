"""Shared setup for tests that need a pre-registration that is overdue, in either of its two ways.

Two kinds, and only one may stop work (Dad, 2026-10-21): a review that reached its count of USES blocks; a
review that is past a DATE does not. Tests of the block need the first; the pair needs the second.
"""

from __future__ import annotations

import time

from divineos.core.ledger import count_events_of_type, log_event
from divineos.core.pre_registrations.store import _get_connection

USE_EVENT = "TEST_PREREG_USE_EVENT"


def make_due_by_use(prereg_id: str) -> None:
    """Turn this pre-registration into one that has reached its count of uses (1 of 1)."""
    baseline = count_events_of_type(USE_EVENT)
    log_event(USE_EVENT, "test", {"k": "v"}, validate=False)
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_after_uses = 1, uses_of = ?, uses_baseline = ? "
            "WHERE prereg_id = ?",
            (USE_EVENT, baseline, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()


def make_overdue_by_date(prereg_id: str, days_ago: float = 3) -> None:
    """Move this pre-registration's review date into the past. It is overdue, and it must not block."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE pre_registrations SET review_ts = ? WHERE prereg_id = ?",
            (time.time() - days_ago * 24 * 3600, prereg_id),
        )
        conn.commit()
    finally:
        conn.close()
