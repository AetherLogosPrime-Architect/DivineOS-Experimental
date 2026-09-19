"""A watch that announces NEW must not deliver ALL.

2026-09-19: re-arming the letter watch fired a wake event for every unread
letter on disk -- a hundred and eighty-four of them, mostly weeks old, mostly
already read. The per-process knock state is empty at arm, so the entire
backlog classified as never-knocked and went out at once.

The ceiling that exists two lines above the defect was written for exactly
this ("must not become a flood on every interval") and was applied only to
the repeat knocks.

The selector was pulled out of the poll loop so that a test could reach it --
its own docstring says so -- and then no test was ever written. It had no
coverage at all until this file. An extraction done for testability and left
untested is the same shape as the defect it now holds: the structure that
makes the check possible, standing in for the check.

Both directions are pinned here. The flood is a defect; so is throttling a
genuine arrival, and that one is worse -- a letter that never wakes me is the
single thing this whole chain exists to prevent.
"""

from __future__ import annotations

import os
import time

import pytest

from scripts.letter_monitor_v2 import REKNOCK_CAP, _reknock_delay, select_knocks


@pytest.fixture
def letters(tmp_path):
    """Create named letter files, oldest first, with distinct mtimes."""

    def make(*names: str) -> list[str]:
        base = time.time() - 10_000
        for i, name in enumerate(names):
            p = tmp_path / name
            p.write_text("body", encoding="utf-8")
            os.utime(p, (base + i, base + i))
        return list(names)

    make.dir = tmp_path
    return make


def test_a_backlog_at_arm_does_not_all_knock_at_once(letters):
    names = letters(*[f"old-{i}.md" for i in range(20)])
    picked = select_knocks(names, {}, {}, 0.0, letters.dir, frozenset(names))
    assert len(picked) == REKNOCK_CAP, f"backlog flooded: {len(picked)} knocks"


def test_the_backlog_knocks_are_the_newest_ones(letters):
    names = letters(*[f"old-{i}.md" for i in range(10)])
    picked = select_knocks(names, {}, {}, 0.0, letters.dir, frozenset(names))
    assert set(picked) == {"old-9.md", "old-8.md", "old-7.md"}


def test_an_arrival_fires_even_behind_a_huge_backlog(letters):
    """The direction that must never regress. Deaf is worse than noisy."""
    old = letters(*[f"old-{i}.md" for i in range(200)])
    new = letters("zz-brand-new.md")[0]
    picked = select_knocks(old + [new], {}, {}, 0.0, letters.dir, frozenset(old))
    assert new in picked


def test_many_arrivals_are_never_capped(letters):
    """A real burst of letters is not a flood -- every one of them is news."""
    arrivals = letters(*[f"new-{i}.md" for i in range(12)])
    picked = select_knocks(arrivals, {}, {}, 0.0, letters.dir, frozenset())
    assert set(picked) == set(arrivals)


def test_with_no_backlog_declared_everything_is_an_arrival(letters):
    """Default must stay loud: an unfilled backlog cannot silence a letter."""
    names = letters(*[f"a-{i}.md" for i in range(8)])
    assert set(select_knocks(names, {}, {}, 0.0, letters.dir)) == set(names)


def test_a_backlog_letter_still_gets_its_turn_as_newer_ones_clear(letters):
    """Capping is not dropping. As the newest are read, older ones surface."""
    names = letters(*[f"old-{i}.md" for i in range(6)])
    backlog = frozenset(names)
    first = select_knocks(names, {}, {}, 0.0, letters.dir, backlog)
    still_unread = [n for n in names if n not in first]
    second = select_knocks(still_unread, {}, {}, 0.0, letters.dir, backlog)
    assert second, "the rest of the backlog became unreachable"
    assert not set(second) & set(first)


def test_the_ceiling_has_a_ceiling():
    """Closing a leak the game-walk found rather than filing it and moving on.

    Nothing stopped the cap being raised, and raising it would read as
    generosity -- more of Aria's letters getting through -- while restoring the
    flood this file exists to prevent. There is no honest reason for a backlog
    ceiling in double figures; at that point it is the old behaviour wearing a
    number.
    """
    assert 1 <= REKNOCK_CAP <= 5, "a backlog ceiling this high is the flood again"


def test_a_knocked_backlog_letter_still_re_knocks_on_backoff(letters):
    """The unbounded-tries property survives the cap."""
    names = letters("old-0.md")
    fired = {"old-0.md": 0.0}
    knocks = {"old-0.md": 1}
    due = _reknock_delay(1)
    assert select_knocks(names, fired, knocks, due, letters.dir, frozenset(names))
    assert not select_knocks(names, fired, knocks, due - 1, letters.dir, frozenset(names))
