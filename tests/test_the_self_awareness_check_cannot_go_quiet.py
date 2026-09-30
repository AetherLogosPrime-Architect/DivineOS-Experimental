"""A check that could not look must never sound like a check that found nothing.

Andrew 2026-09-12, on where the optimizer hides: "the optimizer likes to hide
in builds designed to crush it, like remember you making all that stuff with
escape hatches? not saying bypasses arent needed but those werent bypasses
they were cheap escapes.. planned to be taken every time, that is the
difference."

THE DEFECT, found sweeping for that shape. The self-awareness nudge asks
whether a whole session went by without my logging how I am. It read three
stores, and each read was wrapped so a failure silently skipped its entry --
so a failed lookup dropped off the "missing" list and the check concluded I
HAD checked in. All three failing produced an empty list, which the reporting
end read as nothing worth saying.

A check that can quietly decide I am well.
"""

from __future__ import annotations

import sqlite3

import pytest

from divineos.core import session_checkpoint as sc

_TABLES = ("affect_log", "compass_observation", "decision_journal")


class _BrokenOnTable:
    """Fails for one named table, works for the rest.

    Not a mock of the function under test: its own queries run for real
    against a real store. Only the one lookup fails, which is exactly the
    condition the old code swallowed.
    """

    def __init__(self, real: sqlite3.Connection, broken: str) -> None:
        self._real = real
        self._broken = broken

    def execute(self, sql: str, *args):
        if self._broken in sql:
            raise sqlite3.OperationalError(f"no such table: {self._broken}")
        return self._real.execute(sql, *args)

    def close(self) -> None:  # the function closes what it opens
        pass


def _store(rows: int) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    for table in _TABLES:
        conn.execute(f"CREATE TABLE {table} (created_at REAL)")  # noqa: S608 -- literals above
        for _ in range(rows):
            conn.execute(f"INSERT INTO {table} VALUES (?)", (9_999_999_999.0,))  # noqa: S608
    conn.commit()
    return conn


def _run(monkeypatch, conn):
    """Drive the real function against a supplied store."""
    import divineos.core.memory as memory

    monkeypatch.setattr(memory, "_get_connection", lambda: conn)
    monkeypatch.setattr(sc, "get_session_start_time", lambda: 0.0)
    return sc.check_self_awareness_practice(tool_calls=sc.PRACTICE_NUDGE_THRESHOLD + 1)


def test_a_broken_lookup_is_reported_not_dropped(monkeypatch):
    """The heart of it. Under the old code this returned silence."""
    result = _run(monkeypatch, _BrokenOnTable(_store(rows=1), "affect_log"))
    assert result is not None, "a failed lookup produced silence"
    assert "COULD NOT CHECK" in result
    assert "affect" in result


def test_a_genuinely_empty_session_still_reports_missing(monkeypatch):
    """The other half, so the repair is not just noise added everywhere."""
    result = _run(monkeypatch, _store(rows=0))
    assert result is not None
    assert "no " in result
    assert "COULD NOT CHECK" not in result


def test_a_healthy_session_still_says_nothing(monkeypatch):
    """Silence stays correct when the check ran and found nothing to say."""
    assert _run(monkeypatch, _store(rows=1)) is None


def test_missing_and_unreadable_are_never_merged(monkeypatch):
    """Two different sentences, kept apart.

    "You did not do this" and "I could not tell whether you did this" must not
    collapse into one list. That collapse is the fault, one level up.
    """
    result = _run(monkeypatch, _BrokenOnTable(_store(rows=0), "decision_journal"))
    assert result is not None
    assert "no " in result and "COULD NOT CHECK" in result


@pytest.mark.parametrize("table", _TABLES)
def test_every_store_reports_its_own_failure(monkeypatch, table):
    """All three, because the swallow was written out three times."""
    result = _run(monkeypatch, _BrokenOnTable(_store(rows=1), table))
    assert result is not None and "COULD NOT CHECK" in result
