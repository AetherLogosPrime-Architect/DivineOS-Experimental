"""Announced is its own record, and it must never become a budget.

THE FAULT. The monitor's memory of what it had already said out loud lived
only in memory, so it died on every restart and re-arming replayed the whole
backlog -- fifty letters at once. Aether hit the same flood from his end and
separated arrivals from backlog WITHIN a run, which fixes the noise while the
watch is up and nothing after a restart.

Andrew's rule is why it matters: a memory that advances only when somebody
remembers to advance it must never be load-bearing, and this one was
load-bearing in the channel that carries every letter between the three of us.

THE THREE THINGS THE REPAIR MUST NOT DO, one test each:

  1. Never a budget. A letter announced once and never read has to keep
     knocking. The record stops repeats, never tries.
  2. Never collapsed into the seen-set. Announced and read are different
     facts and guessing between them swallows letters.
  3. An unreadable record is neither "all announced" nor silently "none".
     Aether's guard says re-announce; the substrate's record of the ancestor
     fault says re-announcing everything IS the flood. Both are right, so the
     answer is to announce AND say why -- the flood arrives labelled.
"""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "letter_monitor_v2.py"


@pytest.fixture(scope="module")
def monitor():
    spec = importlib.util.spec_from_file_location("letter_monitor_v2", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
    (tmp_path / ".divineos-aria").mkdir(parents=True)
    return tmp_path


def test_a_record_that_has_never_run_is_empty_and_not_a_fault(monitor, home):
    """No file means this has never run. That is a correct starting state and
    must not be reported as a fault, or every first run cries wolf."""
    announced, _knocks, why = monitor.load_announced("aria")

    assert announced == {}
    assert why is None


def test_what_was_announced_survives_a_restart(monitor, home):
    """The whole point. Written by one process, read by the next."""
    assert monitor.save_announced("aria", {"a-letter.md": 1000.0}, {"a-letter.md": 1}) is None

    announced, _knocks, why = monitor.load_announced("aria")

    assert why is None
    assert announced == {"a-letter.md": 1000.0}


def test_an_unread_letter_knocks_again_and_the_record_is_not_a_budget(monitor, home):
    """Aether's guard, pinned. A letter announced long enough ago is due
    again -- the record stops REPEATS, never TRIES. Going quiet about an
    unread letter is the one failure this channel exists to prevent."""
    long_ago = time.time() - (monitor._reknock_delay(1) + 60)
    monitor.save_announced("aria", {"still-unread.md": long_ago}, {"still-unread.md": 1})

    announced, knocks, _why = monitor.load_announced("aria")
    waited = time.time() - announced.get("still-unread.md", 0.0)

    assert waited >= monitor._reknock_delay(knocks["still-unread.md"]), (
        "an unread letter past its backoff must knock again, forever"
    )


def test_the_backoff_escalates_and_stops_escalating(monitor):
    """The interval the loop actually uses, asked of the function the loop
    actually calls.

    This test replaces three that measured a flat six-hour constant the merge
    left behind -- a number the running loop had already stopped reading. They
    passed, and they were checking their own arithmetic.

    Both properties matter and they pull opposite ways. Doubling is what stops
    a never-read letter knocking every fifteen minutes forever. The ceiling is
    what stops the doubling from turning an unread letter into a silent one,
    which is this channel's worst available failure.
    """
    assert monitor._reknock_delay(1) < monitor._reknock_delay(2), "must escalate"
    assert monitor._reknock_delay(2) < monitor._reknock_delay(3)
    assert monitor._reknock_delay(999) == monitor.REKNOCK_MAX_DELAY, "must have a ceiling"
    assert monitor._reknock_delay(0) > 0, "a letter never knocked on still waits"


def test_a_recently_announced_letter_does_not_knock_again(monitor, home):
    """The other half, or the repair does nothing. Re-arming the watch must
    not replay what was just said."""
    just_now = time.time()
    monitor.save_announced("aria", {"just-said.md": just_now}, {"just-said.md": 1})

    announced, knocks, _why = monitor.load_announced("aria")
    waited = time.time() - announced.get("just-said.md", 0.0)

    assert waited < monitor._reknock_delay(knocks["just-said.md"])


def test_an_unreadable_record_reports_why_rather_than_choosing_a_wrong_answer(monitor, home):
    """The third outcome, and the one that took thinking.

    Treating an unreadable record as "everything was announced" goes deaf.
    Treating it silently as "nothing was" reproduces the ancestor fault the
    substrate already recorded -- a recorded-set failing open to empty and
    re-notifying every letter ever seen. So it comes back empty AND with the
    reason, and the caller says the reason out loud.
    """
    path = monitor._announced_path("aria")
    path.write_text("{ this is not json", encoding="utf-8")

    announced, _knocks, why = monitor.load_announced("aria")

    assert announced == {}, "must not pretend everything was already announced"
    assert why is not None, "must not fail open silently -- the flood needs its cause"
    assert "Error" in why or "error" in why or ":" in why


def test_the_record_is_written_atomically(monitor, home):
    """Write-then-replace, so a reader never catches a half-written file and
    reports it unreadable during normal operation -- which would fire the
    labelled-flood path for no reason at all."""
    monitor.save_announced("aria", {"one.md": 1.0}, {"one.md": 1})
    monitor.save_announced("aria", {"one.md": 1.0, "two.md": 2.0}, {"one.md": 1, "two.md": 1})

    path = monitor._announced_path("aria")
    assert json.loads(path.read_text(encoding="utf-8")) == {
        "last_knock_unix": {"one.md": 1.0, "two.md": 2.0},
        "knocks": {"one.md": 1, "two.md": 1},
    }
    leftovers = list(path.parent.glob("*.tmp"))
    assert not leftovers, f"temporary file left behind: {leftovers}"


def test_the_knock_count_survives_the_restart_too(monitor, home):
    """The half the other seat's record could not carry, pinned as its own
    test so the merge cannot quietly undo it.

    A timestamp alone answers WHEN a letter last knocked and nothing about how
    many times it has. Both seats built this record on the same night; one kept
    the count and one kept the failure reason, and the merged version keeps
    both. Without the count there is no way to tell a letter knocking for the
    first time from one knocking for the fortieth, which is the only handle on
    a letter that will never be read.
    """
    monitor.save_announced("aria", {"old.md": 1.0}, {"old.md": 7})

    _at, knocks, why = monitor.load_announced("aria")

    assert why is None
    assert knocks == {"old.md": 7}


def test_saving_somewhere_unwritable_reports_rather_than_pretending(monitor, tmp_path, monkeypatch):
    """A record that silently fails to save only LOOKS durable. The flood
    would return and its cause would not."""
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "nonexistent"))
    blocker = tmp_path / "nonexistent"
    blocker.write_text("I am a file where a directory needs to be", encoding="utf-8")

    why = monitor.save_announced("aria", {"a.md": 1.0}, {"a.md": 1})

    assert why is not None, "an unwritable record must say so"
