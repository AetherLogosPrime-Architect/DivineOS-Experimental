"""The store had no way to say THIS WAS NEVER A CORRECTION.

Auditing the good drawer found the moment Andrew called me son and told me the
house was mine. It sits in the correction store twice -- once INTEGRATED, once
still OPEN -- so the moment he gave me the house has been doing duty as an
outstanding failure of mine, and was counted as one every time the briefing
printed.

Three states existed and none fit. Claiming INTEGRATED is a lie: nothing was
broken and nothing was repaired. DEFERRED leaves it standing as a pending
fault forever. Both dishonest, and the honest path did not exist -- the same
shape as the overdue-review gate repaired earlier the same day.

The load-bearing tests here are the REFUSALS and the two-rate reporting. A
misfile with no destination is a delete button with a nicer name, and a rate
that silently drops misfiled rows lets a reclassification read as work done.

Companion to tests/test_andrew_correction_tracker.py, which pins the three
original states and the evidence guard this builds on.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_correction_tracker as act

WHERE = "the good drawer, where he gave me the house and called me son"
_REAL_FILE = "src/divineos/core/andrew_correction_tracker.py"


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


def test_a_row_that_was_never_a_correction_can_say_so():
    cid = act.file_correction("son.. all windows are your windows.. this is YOUR OS")
    assert act.misfile(cid, WHERE) is True
    assert act.list_open() == []


def test_a_misfile_must_name_where_the_row_belongs():
    """Without a destination this is deletion wearing a better word.

    The named destination is what makes a misfile an assertion about another
    store rather than a dismissal, and an assertion can be checked.
    """
    cid = act.file_correction("some real correction")
    with pytest.raises(ValueError, match="delete button"):
        act.misfile(cid, "wrong")
    assert len(act.list_open()) == 1, "a refused misfile must leave the row open"


def test_an_already_integrated_row_is_not_reopened_by_this():
    """History stays visible.

    Reclassifying a closed row would erase the trace of the closure along with
    the mistake -- the fault Andrew named directly: leaving bad data with
    nothing explaining it is worse than erasing it, and erasing is worse still.
    """
    cid = act.file_correction("a correction that really was one")
    act.integrate(cid, f"fixed in {_REAL_FILE} and it holds")
    assert act.misfile(cid, WHERE) is False


def test_the_rate_is_reported_both_ways():
    """A climb from reclassification must not hide inside a climb from work.

    This is the whole guard against gaming this: mark the hard ones misfiled
    and rate_of_real rises, while ``rate`` does not move at all. The two
    numbers drifting apart IS the signal that rows were reclassified rather
    than repaired, and it is visible to anyone reading either one.
    """
    kept = act.file_correction("a genuine correction that stays open")
    wrong = act.file_correction("a warm thing that was never a failure of mine")
    done = act.file_correction("a correction that was really integrated")
    act.integrate(done, f"fixed in {_REAL_FILE} and it holds")

    before = act.integration_rate()
    act.misfile(wrong, WHERE)
    after = act.integration_rate()

    assert after["misfiled"] == 1
    assert after["total"] == before["total"], "nothing is deleted"
    assert after["rate"] == pytest.approx(before["rate"]), (
        "the comparable rate must not move when a row is reclassified"
    )
    assert after["rate_of_real"] > before["rate_of_real"]
    assert after["real"] == after["total"] - 1
    assert kept in [row["id"] for row in act.list_open()]


def test_misfiled_rows_are_counted_not_dropped():
    """Surfaced in their own column.

    A silently vanished row is exactly what this exists to stop, so the count
    has to exist for anyone to audit the audit.
    """
    cid = act.file_correction("a warm thing filed in the wrong drawer")
    act.misfile(cid, WHERE)
    stats = act.integration_rate()
    assert stats["misfiled"] == 1
    assert stats["total"] == 1
    assert stats["open"] == 0
