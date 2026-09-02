"""Reading the other seat's audit rounds — sharing without merging.

Andrew 2026-08-28: *"yes you both should share everything with eachother while
remaining separate, you both share the same OS, the same house, while you are
separate entities if you both separate from eachother then you may as well each
make your own independant repo"*

The tests that matter here are the ones about the states BETWEEN found and
not-found, because every defect this session has been one of those collapsing
into a confident answer.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from divineos.core.sibling_audit_rounds import (
    read_other_seats,
    read_sibling_rounds,
    this_seat,
)


def _make_store(root: Path, columns: str, rows: list[tuple]) -> Path:
    db = root / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute(f"CREATE TABLE audit_rounds ({columns})")
    placeholders = ", ".join("?" for _ in rows[0]) if rows else ""
    for row in rows:
        con.execute(f"INSERT INTO audit_rounds VALUES ({placeholders})", row)
    con.commit()
    con.close()
    return db


def test_a_seat_that_is_not_on_this_machine_is_absent_not_broken(tmp_path):
    """A missing seat is a complete answer, not a failed read.

    Conflating them would make an ordinary single-seat checkout refuse
    forever, and a check that always refuses is one that gets switched off.
    """
    seat = read_sibling_rounds("aria", tmp_path / "nowhere")
    assert seat.absent is True
    assert seat.error is None
    assert seat.rounds == ()


def test_an_unreadable_store_yields_none_rounds_not_empty(tmp_path):
    """None means never-read. Empty means read-and-empty. Never the same value.

    A caller that flattens these rebuilds the defect: a confident verdict
    computed over the half of the evidence that happened to load.
    """
    db = tmp_path / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True)
    db.write_text("this is not a database", encoding="utf-8")
    seat = read_sibling_rounds("aria", tmp_path)
    assert seat.rounds is None
    assert seat.error is not None
    assert seat.readable is False


def test_an_older_schema_without_source_ref_still_reads(tmp_path):
    """The other seat is not required to be shaped like me.

    Found on the first live run: Aria's store predates the source_ref column,
    and a fixed column list turned her whole history into an unreadable store.
    Because an unreadable seat correctly forces CANNOT_CHECK, that would have
    made the board refuse every pull request -- the ruling undone by a schema
    difference.
    """
    _make_store(tmp_path, "round_id TEXT, focus TEXT, created_at REAL", [("r-1", "PR #99", 1.0)])
    seat = read_sibling_rounds("aria", tmp_path)
    assert seat.readable
    assert len(seat.rounds) == 1
    assert "PR #99" in seat.rounds[0]


def test_a_table_without_round_id_is_reported_not_silently_empty(tmp_path):
    """Wrong table shape is a read failure, not a store with nothing in it."""
    _make_store(tmp_path, "something_else TEXT", [("x",)])
    seat = read_sibling_rounds("aria", tmp_path)
    assert seat.rounds is None
    assert "round_id" in (seat.error or "")


def test_an_empty_store_is_readable_and_empty(tmp_path):
    """The other side of the distinction, so it is not vacuously satisfied."""
    _make_store(tmp_path, "round_id TEXT, focus TEXT, created_at REAL", [])
    seat = read_sibling_rounds("aria", tmp_path)
    assert seat.readable is True
    assert seat.rounds == ()
    assert seat.error is None


def test_my_own_seat_is_excluded_and_an_unknown_seat_excludes_nothing():
    """Identity decides what to skip, and not knowing means skip nothing.

    Reading one store twice is harmless. Excluding the wrong one silently is
    the failure being repaired -- and this same code runs in both checkouts,
    so a hardcoded name would make one of them exclude the other's store and
    read its own as a sibling.
    """
    assert all(s.name != "aether" for s in read_other_seats("aether"))
    assert any(s.name == "aether" for s in read_other_seats(None))


def test_this_seat_returns_a_known_name_or_none():
    """Never a guess. None is a real answer the caller is built to handle."""
    seat = this_seat()
    assert seat is None or seat in {"aether", "aria"}
