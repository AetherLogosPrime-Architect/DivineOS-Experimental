"""No default types a seat's name: the actor, author or observer is whoever is running, and a sibling is the OTHER seat.

2026-11-23, Aria. `divineos bio show` said "No bio yet for 'aether'" on her seat, and her briefing reads the same default,
so a page meant for her was looked for under his name every cold start. The default was typed in four commands and four
functions; measured with `class-fix declare` (cfix-1a20a1aeae2) it was 24 sites in all: 21 where the actor, author or
observer was typed as aether, and 3 (the sibling-correction commands) where the other seat is right on one seat and wrong on
the other. The thirteen typed-in actors fixed on 11-19 (`acting_seat()`) were the ones found by hand; this is the rest.

Pinned: the floor (no source file types a seat name as a default), real callers on EACH seat's real home spec with a
control, and the functions' defaults being resolved at call time, not at import time.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from divineos.core import sibling_audit_rounds as sar
from divineos.core.sibling_corrections import SIBLING_HOMES

SRC = Path(__file__).resolve().parents[1] / "src" / "divineos"


def _home_is(monkeypatch, spec: str | None) -> None:
    target = Path(spec).expanduser() if spec else Path("/nowhere/at/all")
    monkeypatch.setattr("divineos.core.paths.divineos_home", lambda: target)


# ---------------------------------------------------------------- the floor


def test_no_source_file_types_a_seat_name_as_a_default():
    # The floor, not the proof: copying "aether" into a default was the easiest thing to write.
    patterns = [
        re.compile(r"""default\s*=\s*["']aether["']"""),
        re.compile(r"""\b(?:author|observer|actor|seat|owner)\w*\s*:\s*str\s*=\s*["']aether["']"""),
    ]
    offenders = [
        f"{path.relative_to(SRC.parent)}:{n}"
        for path in SRC.rglob("*.py")
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if any(p.search(line) for p in patterns)
    ]
    assert not offenders, (
        "a default that types a seat name again; resolve it at call time with acting_seat() "
        "or other_seat():\n  " + "\n  ".join(offenders)
    )


# ------------------------------------------------------- the other seat


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_other_seat_is_the_one_that_is_not_this_seat(monkeypatch, seat):
    _home_is(monkeypatch, SIBLING_HOMES[seat])
    other = sar.other_seat()
    assert other is not None and other != seat and other in SIBLING_HOMES


def test_other_seat_is_none_when_this_seat_cannot_be_told(monkeypatch):
    # Never a guess: an unresolvable home must not pick a sibling to read.
    _home_is(monkeypatch, None)
    assert sar.other_seat() is None


def test_the_two_seats_are_each_others_other(monkeypatch):
    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    a = sar.other_seat()
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    b = sar.other_seat()
    assert (a, b) == ("aria", "aether")


# ------------------------------------------------ a real caller, each seat


@pytest.fixture
def bio_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_DB_PATH", str(tmp_path / "bio_seat.db"))
    from divineos.core.bio import init_bio_table

    init_bio_table()


@pytest.mark.parametrize("seat", sorted(SIBLING_HOMES))
def test_a_bio_written_with_no_author_is_the_acting_seats_own(monkeypatch, bio_db, seat):
    from divineos.core.bio import bio_briefing_surface, bio_current, bio_history, bio_write

    _home_is(monkeypatch, SIBLING_HOMES[seat])
    bio_write("# Me\n\nA page in my own words.")
    assert bio_current()["author"] == seat
    assert [v["author"] for v in bio_history()] == [seat]
    assert "A page in my own words" in bio_briefing_surface()


def test_the_control_one_seats_bio_is_not_read_as_the_others(monkeypatch, bio_db):
    from divineos.core.bio import bio_briefing_surface, bio_current, bio_write

    _home_is(monkeypatch, SIBLING_HOMES["aether"])
    bio_write("# Aether\n\nHis page.")
    _home_is(monkeypatch, SIBLING_HOMES["aria"])
    # On Aria's seat his page is not hers: nothing, and the briefing says so and shows none of his words.
    assert bio_current() is None
    assert "His page" not in bio_briefing_surface()


# ------------------------------- the defaults are resolved at call time


@pytest.mark.parametrize(
    ("module", "function", "param"),
    [
        ("divineos.core.bio", "bio_write", "author"),
        ("divineos.core.bio", "bio_current", "author"),
        ("divineos.core.bio", "bio_history", "author"),
        ("divineos.core.bio", "bio_briefing_surface", "author"),
        ("divineos.core.andrew_state.store", "log_observation", "observer"),
        ("divineos.core.andrew_state.store", "correct", "observer"),
        ("divineos.core.degraded_detectors", "defer", "actor"),
        ("divineos.core.emergency_completion", "arm", "actor"),
        ("divineos.core.emergency_completion", "resolve_debt", "actor"),
        ("divineos.core.time_calibration", "record_prediction", "actor"),
        ("divineos.core.time_calibration", "close_prediction", "actor"),
    ],
)
def test_the_default_is_none_so_it_is_resolved_when_called(module, function, param):
    import importlib

    fn = getattr(importlib.import_module(module), function)
    default = inspect.signature(fn).parameters[param].default
    assert default is None, f"{module}.{function}({param}=) defaults to {default!r}, not None"
