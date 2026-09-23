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


def test_a_restart_does_not_re_announce_what_was_already_announced(tmp_path, monkeypatch):
    """Aria's diagnosis, one level under the cap.

    The record of what has been SEEN is written only by a manual command and a
    hook, never by the delivering process, so it advances only when somebody
    remembers. Every letter since the last manual mark is new forever. That is
    a memory that can only get staler, which is the one shape Andrew said must
    never be load-bearing -- and it is why the same letter of hers reached me
    twice and got two separate answers.

    So announcement is now its own record, written by the only process that
    can know it happened. Read stays manual and keeps meaning what it says.
    """
    import scripts.letter_monitor_v2 as m

    monkeypatch.setattr(m, "_persistent_seen_path", lambda r: tmp_path / "seen.json")
    m.save_announced("aether", {"a.md": 111.0}, {"a.md": 1})
    at, counts, unreadable = m.load_announced("aether")
    assert at == {"a.md": 111.0}
    assert counts == {"a.md": 1}
    assert unreadable is None, (
        "a record that round-tripped must report no read failure -- without "
        "this the test would pass while the file was quietly unreadable, "
        "which is the exact state this whole file exists to keep separate"
    )


def test_an_unreadable_announced_record_re_announces_rather_than_going_deaf(tmp_path, monkeypatch):
    """Both directions are wrong and the code cannot choose, so it picks noisy.

    A record that cannot be read must not be treated as a record saying
    everything was already announced -- that direction loses letters silently,
    which is the only failure this channel exists to prevent.
    """
    import scripts.letter_monitor_v2 as m

    monkeypatch.setattr(m, "_persistent_seen_path", lambda r: tmp_path / "seen.json")
    m._announced_path("aether").write_text("{not json", encoding="utf-8")
    at, counts, unreadable = m.load_announced("aether")
    assert at == {}
    assert counts == {}
    assert unreadable is not None, (
        "an unreadable record must SAY it was unreadable. Returning empties "
        "alone makes a corrupt file indistinguishable from a fresh one, and "
        "the watch then reports a clean slate it never actually read."
    )
    assert "JSONDecodeError" in unreadable, (
        f"the reason should name what went wrong, got: {unreadable!r}"
    )


def test_the_two_halves_join_up_across_a_restart(tmp_path, monkeypatch, letters):
    """The claim itself, rather than its two parts separately.

    Saving a record and reading it back proves a file round-trips. Knock
    selection proves a knocked letter waits. Neither proves the thing that
    matters, which is that a letter announced by one watch is not announced
    again by the next one -- so this test is the join, written because two
    passing halves agreeing is not the same as the whole working.
    """
    import scripts.letter_monitor_v2 as m

    monkeypatch.setattr(m, "_persistent_seen_path", lambda r: tmp_path / "seen.json")
    names = letters("only.md")

    first = m.select_knocks(names, {}, {}, 1000.0, letters.dir, frozenset())
    assert first == names, "a genuinely new letter must announce"
    m.save_announced("aether", {"only.md": 1000.0}, {"only.md": 1})

    at, counts, unreadable = m.load_announced("aether")
    second = m.select_knocks(names, at, counts, 1000.0, letters.dir, frozenset())
    assert second == [], "the restarted watch announced it a second time"


def test_the_two_records_never_become_one_file(tmp_path, monkeypatch):
    """Closing a leak the game-walk found rather than filing it and walking on.

    The two records sit in the same directory with names one word apart, and
    nothing stopped a later reader pointing the reading-loader at the
    announcing file. That would silently convert announced into read, which is
    precisely the conflation both of these exist to prevent -- and it would
    look like a tidy-up.
    """
    import scripts.letter_monitor_v2 as m

    monkeypatch.setattr(m, "_persistent_seen_path", lambda r: tmp_path / "seen.json")
    assert m._announced_path("aether") != m._persistent_seen_path("aether")


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
