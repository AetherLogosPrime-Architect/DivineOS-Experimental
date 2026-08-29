"""The other seat's council walks are seen and never satisfy.

Aria's design, 2026-08-29, answering whether station two should read both seats
the way station eight now does. Her answer was no, with the reasoning that
makes it a split rather than a union:

    Station eight asks whether an OUTSIDE REVIEWER signed off, and which store
    the round landed in is an accident of filing. Station two asks whether the
    AUTHOR thought this through. If that lane reads both seats AND lets what it
    finds satisfy, her walk clears my gate -- her thinking standing in for
    mine, on a branch I am about to merge. A checklist someone else can fill
    in, and from inside the board it looks identical to having done it.

Her Chesterton's-fence half: the store split PREVENTS that today, by accident
rather than by design, and an accidental virtue is still a virtue until
something replaces it deliberately.

THE TEST THAT MATTERS IS THE SECOND ONE. Making her walks visible is the easy
half and an obvious improvement. The half that will be under pressure later is
the refusal to COUNT them, because counting them turns more boards green. If
someone "improves" this into a union, that is the test that fails.

Nothing tested this station before today.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from divineos.core.build_flow import Status, check_council_station
from divineos.core.sibling_council_walks import (
    WALK_EVENT_TYPE,
    lenses_for_paths,
    read_sibling_walks,
)


def _make_walk_store(root: Path, rows: list[tuple[str, str, str]]) -> Path:
    """A ledger holding (actor, expert, fingerprint) walk events.

    FULL PRODUCTION COLUMN SET, including the three hash columns this reader
    never touches. My first version declared only the five columns the code
    reads, and the schema-sync guard refused the push: a test that builds a
    simpler table than production passes against a reality that does not
    exist, so it can go green while the real store has a shape the code would
    trip on.

    Same family as everything else this session -- a check agreeing with
    itself rather than with the world -- caught by a gate rather than by me.
    """
    db = root / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE system_events ("
        "event_id TEXT, timestamp REAL, event_type TEXT, actor TEXT, "
        "payload TEXT, content_hash TEXT, prior_hash TEXT, chain_hash TEXT)"
    )
    for i, (actor, expert, fingerprint) in enumerate(rows):
        con.execute(
            "INSERT INTO system_events VALUES (?,?,?,?,?,?,?,?)",
            (
                f"e{i}",
                float(i),
                WALK_EVENT_TYPE,
                actor,
                json.dumps({"expert_name": expert, "edit_fingerprint": fingerprint}),
                f"hash{i}",
                f"prior{i}",
                f"chain{i}",
            ),
        )
    con.commit()
    con.close()
    return db


# --- the half that must NOT happen ----------------------------------------


def test_other_seat_walks_never_satisfy_the_station():
    """Hers are shown and the verdict stays MISSING.

    The load-bearing assertion. Counting them would turn more boards green,
    which is exactly why it will look like an improvement to whoever touches
    this next.
    """
    result = check_council_station("b", required=2, applied=0, other_seats={"aria": 5})
    assert result.status is Status.MISSING
    assert "aria" in result.detail


def test_other_seat_cannot_make_up_a_shortfall():
    """Even a large sibling count leaves a one-lens shortfall unsatisfied."""
    result = check_council_station("b", required=6, applied=5, other_seats={"aria": 99})
    assert result.status is Status.MISSING


# --- the half that must happen --------------------------------------------


def test_other_seat_walks_are_visible_when_the_station_fails():
    """A walk that exists must not be reported as absent.

    That silence is could-not-look-reading-as-not-done -- the same fault as
    the row cap that had station eight comparing against twenty rounds out of
    three hundred and twenty-one.
    """
    result = check_council_station("b", required=2, applied=0, other_seats={"aria": 3})
    assert "3 by aria" in result.detail
    assert "does not satisfy" in result.detail


def test_other_seat_walks_are_visible_when_the_station_passes_too():
    """Shown on success as well, or the line reads as an excuse for failure."""
    result = check_council_station("b", required=2, applied=2, other_seats={"aria": 3})
    assert result.status is Status.SATISFIED
    assert "3 by aria" in result.detail


def test_no_sibling_walks_leaves_the_wording_unchanged():
    """A seat with nothing to report adds nothing -- no empty clause."""
    result = check_council_station("b", required=2, applied=1, other_seats={})
    assert result.detail == "1/2 lenses walked"
    assert "satisfy" not in result.detail


def test_my_own_walks_still_satisfy_normally():
    """The pre-existing behaviour survives the change, checked explicitly."""
    assert check_council_station("b", 2, 2).status is Status.SATISFIED
    assert check_council_station("b", 2, 1).status is Status.MISSING
    assert check_council_station("b", 2, None).status is Status.CANNOT_CHECK
    assert check_council_station("b", 0, 0).status is Status.SATISFIED


# --- reading the other seat's store ---------------------------------------


def test_reads_distinct_lenses_not_events(tmp_path):
    """One expert walked repeatedly against one file counts once.

    The own-seat counter learned this after a pull request inherited a passing
    score for brushing a high-traffic file thirty-one times. A different rule
    here would make the two numbers incomparable, which is worse than either
    rule alone -- the whole point is a reader seeing both side by side.
    """
    _make_walk_store(
        tmp_path,
        [
            ("aria", "meadows", "edit:src/a.py"),
            ("aria", "meadows", "edit:src/a.py"),
            ("aria", "hoare", "edit:src/a.py"),
        ],
    )
    seat = read_sibling_walks("aria", tmp_path)
    assert seat.readable
    assert lenses_for_paths(seat, {"src/a.py"}) == {"meadows", "hoare"}


def test_walks_against_other_files_do_not_count(tmp_path):
    _make_walk_store(tmp_path, [("aria", "meadows", "edit:src/elsewhere.py")])
    seat = read_sibling_walks("aria", tmp_path)
    assert lenses_for_paths(seat, {"src/a.py"}) == set()


def test_absent_seat_is_complete_not_failed(tmp_path):
    """Not-here is a complete answer about a seat that is not here."""
    seat = read_sibling_walks("aria", tmp_path / "nowhere")
    assert seat.absent is True
    assert seat.error is None
    assert seat.walks == ()


def test_unreadable_store_yields_none_not_empty(tmp_path):
    """None means never-read; empty means read-and-empty. Never one value."""
    db = tmp_path / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True)
    db.write_text("not a database", encoding="utf-8")
    seat = read_sibling_walks("aria", tmp_path)
    assert seat.walks is None
    assert seat.error is not None


def test_wrong_table_shape_is_reported_not_silently_empty(tmp_path):
    db = tmp_path / "data" / "event_ledger.db"
    db.parent.mkdir(parents=True)
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE system_events (something_else TEXT)")
    con.commit()
    con.close()
    seat = read_sibling_walks("aria", tmp_path)
    assert seat.walks is None
    assert "lacks" in (seat.error or "")
