"""A timing budget must fail for slow CODE and never for a slow MACHINE.

THE DEFECT, 2026-09-21. The event-emission timing tests carried a fixed
wall-clock budget scaled by a hand-set multiplier. That multiplier had already
been raised once, on 2026-07-16, after a flake on a loaded runner. It flaked
again at 6.039s against a 4.0s budget during a full-suite run, with nothing
about the emission code changed, and blocked a push that had nothing to do with
it.

A fixed wall-clock budget collapses two states into one output: "this code got
slower" and "this machine was busy" produce the identical failure, with the
identical message, and the reader cannot tell which happened. Raising the
multiplier is not a repair -- it widens the window in which both states are
still indistinguishable, and guarantees a third flake at a larger number.

The repair is to calibrate in the same process, against the same disk, at the
moment of the test: time a bare sqlite insert loop and require our emission
layer to stay within a multiple of that. Machine speed then divides out.

THE TEST THAT CARRIES THE CLAIM is the pairwise one at the bottom: a machine
ten times slower must get a budget ten times larger, because that is the whole
difference between the old instrument and this one. The individual cases all
still pass if the budget quietly ignores its calibration and returns a
constant -- which is precisely the shape being removed.
"""

from __future__ import annotations

import sqlite3

import pytest

from tests.test_hook_realtime import (
    _EMIT_OVERHEAD_RATIO,
    _emit_budget,
    _seconds_per_bare_insert,
)


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "calib.db"
    sqlite3.connect(str(path)).close()
    return str(path)


def test_the_calibration_measures_something_real(db) -> None:
    """A measurement, not a constant: it must be positive and finite."""
    per = _seconds_per_bare_insert(db, samples=20)
    assert per > 0.0, "calibration returned zero, so every budget would be zero"
    assert per < 5.0, f"one bare insert reported as {per:.3f}s, which is not a measurement"


def test_the_calibration_never_returns_zero_on_a_coarse_clock(db) -> None:
    """Zero would make every budget zero and every timing test fail forever.

    A clock too coarse to see the loop must report its own resolution rather
    than the zero it literally observed -- could-not-measure is not no-time.
    """
    per = _seconds_per_bare_insert(db, samples=1)
    assert per > 0.0


def test_the_budget_leaves_room_above_the_bare_cost(db) -> None:
    """Emission validates, serialises and hash-chains, so it is legitimately
    heavier than a bare insert. The budget must allow that."""
    per = _seconds_per_bare_insert(db, samples=20)
    assert _emit_budget(db, 1) > per


def test_the_budget_is_still_bounded(db) -> None:
    """The repair must not become "anything passes".

    If the budget were unbounded the test would stop detecting regressions,
    which is the over-correction that trades one broken instrument for a
    disconnected one.
    """
    per = _seconds_per_bare_insert(db, samples=20)
    budget = _emit_budget(db, 10)
    ceiling = per * 10 * _EMIT_OVERHEAD_RATIO * 1000
    assert budget < ceiling, "the budget has no ceiling, so no regression can fail it"


def test_a_slower_machine_gets_a_proportionally_larger_budget(monkeypatch, db) -> None:
    """THE CLAIM. Ten times slower disk, ten times the budget.

    Every case above passes if _emit_budget ignores the calibration and returns
    a constant. This one does not: it is the difference between measuring the
    code and measuring the clock.
    """
    import tests.test_hook_realtime as mod

    monkeypatch.setattr(mod, "_seconds_per_bare_insert", lambda *a, **k: 0.001)
    fast = mod._emit_budget(db, 50)
    monkeypatch.setattr(mod, "_seconds_per_bare_insert", lambda *a, **k: 0.010)
    slow = mod._emit_budget(db, 50)

    assert slow > fast, "a slower machine did not get a larger budget"
    assert slow == pytest.approx(fast * 10, rel=1e-6), (
        f"budget did not scale with machine speed: {fast} -> {slow}, expected 10x"
    )


def test_the_budget_scales_with_how_much_work_is_asked_for(monkeypatch, db) -> None:
    """Fifty events may cost fifty times one event, not the same as one."""
    import tests.test_hook_realtime as mod

    monkeypatch.setattr(mod, "_seconds_per_bare_insert", lambda *a, **k: 0.001)
    assert mod._emit_budget(db, 50) == pytest.approx(mod._emit_budget(db, 1) * 50, rel=1e-6)
