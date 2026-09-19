"""Freshness beside emptiness — the death the dead-architecture alarm could not see.

The alarm asked whether a store was EMPTY. A store that filled, worked and then
stopped being fed is not empty, so full-and-abandoned rendered identically to
full-and-thriving. Found 2026-09-19 when the wins ledger turned out to have been
silent for three weeks while a health report used it as a denominator.

Each verdict is proved reachable by construction. An instrument that flagged
everything would be as useless as one that flagged nothing, and would pass the
stale tests by always crying.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from divineos.core.dead_architecture_alarm import _newest_row_age_days, scan_stale_stores

DAY = 86400.0


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    yield c
    c.close()


def _table(c, name, cols, rows):
    c.execute(f"CREATE TABLE {name} ({cols})")
    for r in rows:
        c.execute(f"INSERT INTO {name} VALUES ({','.join('?' * len(r))})", r)
    c.commit()


def test_a_full_but_long_quiet_store_is_dated_as_old(conn):
    _table(conn, "quiet", "id INTEGER, timestamp REAL", [(1, time.time() - 40 * DAY)])
    age, reason = _newest_row_age_days(conn, "quiet")
    assert age is not None
    assert 39 < age < 41
    assert "timestamp" in reason


def test_a_current_store_is_not_old(conn):
    """Non-vacuity: the scan must be able to say FINE, or crying is its only mode."""
    _table(conn, "busy", "id INTEGER, timestamp REAL", [(1, time.time() - 0.5 * DAY)])
    age, _ = _newest_row_age_days(conn, "busy")
    assert age is not None
    assert age < 1


def test_a_store_with_no_time_column_is_unchecked_never_fresh(conn):
    """A store I cannot date is not a store I have cleared."""
    _table(conn, "undateable", "id INTEGER, label TEXT", [(1, "x")])
    age, reason = _newest_row_age_days(conn, "undateable")
    assert age is None, "undateable must not resolve to a number"
    assert "no recognisable time column" in reason
    assert "label" in reason, "the reason names what the table DOES have"


def test_a_null_timestamp_column_is_unchecked_not_zero_days(conn):
    _table(conn, "nulls", "id INTEGER, timestamp REAL", [(1, None)])
    age, reason = _newest_row_age_days(conn, "nulls")
    assert age is None
    assert "null" in reason


def test_an_iso_string_timestamp_is_still_dated(conn):
    """Some stores write text dates. Unparseable is UNCHECKED; parseable is not."""
    old = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() - 30 * DAY))
    _table(conn, "isotable", "id INTEGER, created_at TEXT", [(1, old)])
    age, _ = _newest_row_age_days(conn, "isotable")
    assert age is not None
    assert 29 < age < 31


def test_an_unparseable_timestamp_is_unchecked(conn):
    _table(conn, "junk", "id INTEGER, timestamp TEXT", [(1, "soon-ish")])
    age, reason = _newest_row_age_days(conn, "junk")
    assert age is None
    assert "unparseable" in reason


def test_the_real_scan_reports_both_kinds_separately():
    """Against the live substrate: quiet stores carry a number, unchecked carry None.

    The two must not blur. Collapsing them recreates the original fault one
    level up -- an unknown filed among the cleared.
    """
    stores = scan_stale_stores()
    for s in stores:
        if s.days_quiet is None:
            assert s.reason.startswith("UNCHECKED")
        else:
            assert s.days_quiet > 0
            assert not s.reason.startswith("UNCHECKED")


def test_an_empty_store_is_left_to_the_emptiness_check(conn):
    """Freshness does not duplicate dormancy; zero rows is the other check's job."""
    _table(conn, "empty", "id INTEGER, timestamp REAL", [])
    age, reason = _newest_row_age_days(conn, "empty")
    assert age is None
    assert "null" in reason or "unparseable" in reason or "no recognisable" in reason
