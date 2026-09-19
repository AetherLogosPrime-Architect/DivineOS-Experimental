"""Controls for the review window, built 2026-09-12 after the deadlock.

The overdue gate refused the evidence for two of its own reviews in one night,
leaving a fabricated verdict or a deferral as the only exits. These pin the
properties that make the new path a path rather than a bypass.

The thing to watch on this file: every test here could be made to pass by
loosening ``open_window``. The load-bearing ones are the REFUSALS -- a window
that opens for a review nobody owes, or opens on a one-word purpose, is the
bypass this was built not to be.

Companion to tests/test_overdue_prereg_block.py, which pins the gate's
blocking behaviour. That file must keep passing: a repair that opens the gate
generally, rather than opening it for a declared review, would show up there.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from divineos.core.pre_registrations import review_window as rw

_OVERDUE = "prereg-test-overdue-0001"
_NOT_OVERDUE = "prereg-test-current-0002"
_PURPOSE = "read the merge checker and hand it a fabricated round id to see what it returns"


class _FakePrereg:
    def __init__(self, prereg_id: str) -> None:
        self.prereg_id = prereg_id


@pytest.fixture(autouse=True)
def _scratch_store(monkeypatch, tmp_path):
    """One overdue pre-registration, and a scratch window store."""
    db = tmp_path / "windows.db"
    monkeypatch.setattr(rw, "_get_connection", lambda: sqlite3.connect(db))
    monkeypatch.setattr(
        "divineos.core.pre_registrations.store.get_overdue_pre_registrations",
        lambda now=None: [_FakePrereg(_OVERDUE)],
    )
    yield


def test_a_window_opens_on_a_review_that_is_actually_overdue():
    state = rw.open_window(_OVERDUE, "aether", _PURPOSE)
    assert state.state == "open"
    assert state.prereg_id == _OVERDUE


def test_it_refuses_a_review_nobody_is_owed():
    """The property that separates this from a skeleton key.

    If a window could open against any id, it would stand down the gate
    whenever that was convenient, which is precisely the bypass shape.
    """
    with pytest.raises(rw.WindowRefused, match="not overdue"):
        rw.open_window(_NOT_OVERDUE, "aether", _PURPOSE)


def test_a_one_word_purpose_is_refused():
    """The purpose is the whole cost of the window. Without it this is a flag."""
    with pytest.raises(rw.WindowRefused, match="not a purpose"):
        rw.open_window(_OVERDUE, "aether", "review")


def test_a_zero_length_window_is_refused():
    with pytest.raises(rw.WindowRefused, match="bypass with extra steps"):
        rw.open_window(_OVERDUE, "aether", _PURPOSE, minutes=0)


def test_the_window_expires_on_its_own():
    """Time-bounded, so a forgotten window is not an open door forever."""
    now = time.time()
    rw.open_window(_OVERDUE, "aether", _PURPOSE, minutes=10, now=now)
    assert rw.active_window(now=now + 60).state == "open"
    assert rw.active_window(now=now + 11 * 60).state == "none"


def test_an_assessment_closes_the_window_and_it_stops_counting_as_lapsed():
    now = time.time()
    rw.open_window(_OVERDUE, "aether", _PURPOSE, minutes=10, now=now)
    assert rw.close_windows_for(_OVERDUE) == 1
    assert rw.lapsed_windows(now=now + 11 * 60) == []


def test_a_window_with_no_assessment_behind_it_becomes_a_row():
    """The measurement. Without this the mechanism could not be falsified.

    An earned window and a bypass look identical in the moment; the only thing
    that ever tells them apart is whether an assessment followed, and that is
    knowable only afterwards. So it is recorded afterwards.
    """
    now = time.time()
    rw.open_window(_OVERDUE, "aether", _PURPOSE, minutes=10, now=now)
    lapsed = rw.lapsed_windows(now=now + 11 * 60)
    assert len(lapsed) == 1
    assert lapsed[0][0] == _OVERDUE
    assert lapsed[0][2] == 1


def test_a_store_that_will_not_answer_is_not_a_report_of_no_window(monkeypatch):
    """could-not-check must never read as none.

    If it did, a broken store would silently restore the gate's ordinary deny
    text and nobody could tell a refusal-after-looking from a refusal-without-
    looking. That is the exact fault this house spent the night removing from
    three other checkers.
    """

    def _jammed():
        raise OSError("the drawer is jammed")

    monkeypatch.setattr(rw, "_get_connection", _jammed)
    state = rw.active_window()
    assert state.state == "could-not-check"
    assert "jammed" in state.reason
