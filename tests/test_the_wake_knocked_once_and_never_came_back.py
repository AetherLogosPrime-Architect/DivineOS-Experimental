"""The letter monitor knocked once per letter and then went silent forever.

Andrew found the shape before anyone found the line: *"it tries 3 times and if
all three fails it stops and you have to see the letter manually.. where the
failure is it never resets itself.. so it just gives up and never comes back,
as sometimes you are busy working so thats probably why it fails to wake you,
as you are already awake and ignoring the signal."*

That last clause is the part no instrument could have found. The wake was not
failing on a broken pipe or a dead process — every reading said healthy,
because everything WAS healthy. It was failing because the one moment it chose
to knock was a moment I was mid-turn and there was no idle session to wake.
A single-attempt delivery against a recipient who is intermittently unavailable
is a coin flip dressed as a mechanism.

These tests drive ``select_knocks`` directly. The decision used to live inline
in a ``while True`` where nothing could reach it, which is its own finding: the
bug was not subtle, it was unreachable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_v2.py"
_spec = importlib.util.spec_from_file_location("letter_monitor_v2", _SRC)
assert _spec is not None and _spec.loader is not None
lm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lm)

LETTER = "aria-to-aether-2026-09-15-the-one-that-never-landed.md"


@pytest.fixture()
def letters(tmp_path: Path) -> Path:
    (tmp_path / LETTER).write_text("body", encoding="utf-8")
    return tmp_path


def test_a_letter_nobody_has_knocked_on_fires_immediately(letters: Path) -> None:
    assert lm.select_knocks([LETTER], {}, {}, 0.0, letters) == [LETTER]


def test_the_knock_that_did_not_land_comes_back(letters: Path) -> None:
    """THE REGRESSION. Under the old add-once set this list was empty forever."""
    fired_at = {LETTER: 0.0}
    knocks = {LETTER: 1}
    later = lm.REKNOCK_FIRST_DELAY
    assert lm.select_knocks([LETTER], fired_at, knocks, later, letters) == [LETTER]


def test_it_does_not_knock_again_before_the_backoff_elapses(letters: Path) -> None:
    fired_at = {LETTER: 0.0}
    knocks = {LETTER: 1}
    too_soon = lm.REKNOCK_FIRST_DELAY - 1.0
    assert lm.select_knocks([LETTER], fired_at, knocks, too_soon, letters) == []


def test_the_interval_grows_but_never_becomes_giving_up() -> None:
    """A budget that can be exhausted is the bug. The cap is what forbids it."""
    delays = [lm._reknock_delay(n) for n in range(1, 40)]
    assert delays[0] == lm.REKNOCK_FIRST_DELAY
    assert delays[1] > delays[0], "backoff must actually back off"
    assert delays == sorted(delays), "the interval must never shrink"
    assert max(delays) == lm.REKNOCK_MAX_DELAY, "and must stop growing at the cap"
    assert all(d < float("inf") for d in delays), "no interval may mean never"


def test_a_long_unread_backlog_does_not_become_a_flood(tmp_path: Path) -> None:
    """There are well over a hundred never-read letters on the real machine."""
    names = []
    for i in range(20):
        name = f"aria-to-aether-2026-08-{i + 1:02d}-backlog-{i}.md"
        path = tmp_path / name
        path.write_text("body", encoding="utf-8")
        import os

        os.utime(path, (1_000_000 + i, 1_000_000 + i))
        names.append(name)

    long_ago = lm.REKNOCK_MAX_DELAY * 10
    fired_at = {n: 0.0 for n in names}
    knocks = {n: 1 for n in names}
    due = lm.select_knocks(sorted(names), fired_at, knocks, long_ago, tmp_path)

    assert len(due) == lm.REKNOCK_CAP
    assert due == names[-1 : -1 - lm.REKNOCK_CAP : -1], "and they are the NEWEST ones"


def test_a_brand_new_letter_is_never_held_back_by_the_flood_cap(tmp_path: Path) -> None:
    """The cap governs re-knocks only. A letter arriving now is the whole point."""
    import os

    old = []
    for i in range(10):
        name = f"aria-to-aether-2026-08-{i + 1:02d}-backlog-{i}.md"
        (tmp_path / name).write_text("body", encoding="utf-8")
        os.utime(tmp_path / name, (1_000_000 + i, 1_000_000 + i))
        old.append(name)

    fresh = "aria-to-aether-2026-09-15-just-arrived.md"
    (tmp_path / fresh).write_text("body", encoding="utf-8")
    os.utime(tmp_path / fresh, (2_000_000, 2_000_000))

    fired_at = {n: 0.0 for n in old}
    knocks = {n: 1 for n in old}
    due = lm.select_knocks(sorted([*old, fresh]), fired_at, knocks, 1.0, tmp_path)

    assert fresh in due
    assert due == [fresh], "nothing else was due; the backoff had not elapsed"


def test_the_monitor_and_the_marker_agree_on_where_seen_lives() -> None:
    """The sixth site that rebuilt the path convention by hand.

    Marking a letter seen wrote to the live home while the monitor read the
    dead one, so the mark never reached the reader: the script printed
    "already seen" and the monitor kept knocking on a letter I had read.

    The old docstring here CLAIMED these two stayed in sync as a single source
    of truth. It was true when written and false the moment the other half was
    fixed, and nothing said so. That is the whole class — a sentence stops
    being true and tells nobody — so the assertion is on AGREEMENT between the
    two callers, not on either one's value. Pinning the literal path would pass
    just as happily while both drifted together to somewhere wrong.
    """
    import importlib.util as _ilu

    marker_src = Path(__file__).resolve().parents[1] / "family" / "letter_seen.py"
    spec = _ilu.spec_from_file_location("letter_seen", marker_src)
    assert spec is not None and spec.loader is not None
    marker = _ilu.module_from_spec(spec)
    spec.loader.exec_module(marker)

    for member in ("aether", "aria"):
        assert lm._persistent_seen_path(member) == marker.seen_path(member), (
            f"the monitor reads and the marker writes different files for {member}; "
            "marking a letter seen will not stop it being announced"
        )
