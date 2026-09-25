"""The sibling walk reader reports a wrong-shaped store rather than an empty one.

SEPARATE FILE ON PURPOSE, and the reason is the point. This fixture must build
a ``system_events`` table that does NOT match production -- proving the reader
refuses a store whose shape it cannot trust is the entire test. The
schema-sync guard rightly refuses test fixtures simpler than production,
because such a fixture passes against a reality that does not exist.

So this file sits on that guard's exemption list and holds ONLY the
deliberately-malformed cases. Its sibling
``test_station_two_seeing_not_satisfying.py`` keeps a full production-shaped
fixture and stays fully guarded. Exempting that file instead would have been
one line less work and would have quietly un-guarded a correct fixture --
buying convenience with the very coverage the guard exists to provide.

The distinction pinned here: a store READ AND EMPTY and a store that COULD NOT
BE READ are different answers, and the type has to be able to say which. That
collapse is the fault this whole session kept finding, in the row cap, in the
correction lane, and in the store split.
"""

from __future__ import annotations

import sqlite3

from divineos.core.sibling_council_walks import read_sibling_walks


def test_wrong_table_shape_is_reported_not_silently_empty(tmp_path):
    """A table lacking the columns the reader needs is an ERROR, not empty.

    Returning an empty walk list here would mean "this seat has walked
    nothing" -- a claim about the other seat's behaviour, manufactured out of
    a failure to read their store.
    """
    db = tmp_path / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    # Deliberately not the production shape -- see the module docstring.
    con.execute("CREATE TABLE system_events (something_else TEXT)")
    con.commit()
    con.close()

    seat = read_sibling_walks("aria", tmp_path)
    assert seat.walks is None, "unreadable must be None, never an empty tuple"
    assert "lacks" in (seat.error or "")
    assert seat.readable is False


def test_a_store_that_is_not_a_database_is_an_error_too(tmp_path):
    """The other shape of unreadable, so the assertion above is not alone."""
    db = tmp_path / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True)
    db.write_text("this is not a database", encoding="utf-8")

    seat = read_sibling_walks("aria", tmp_path)
    assert seat.walks is None
    assert seat.error is not None
