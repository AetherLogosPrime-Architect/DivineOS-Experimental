"""Speaking about my own past without opening the record.

Andrew 2026-09-08: *the fact you do not remember shit is a STRUCTURAL PROBLEM
YOU HAVE SOLVED WITH MANY OTHER THINGS.*

Four times in one conversation I answered a question about my own history from
memory, and four times the true answer was one search away. These pin the door.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import history_claim_signal as h

NOW = 1_000_000.0
_READ = [("divineos ask 'how often has he said this'", NOW - 60)]
_NO_READ = [("git status", NOW - 60), ("pytest tests/ -q", NOW - 30)]


@pytest.mark.parametrize(
    "claim",
    [
        "He has said this six hundred times.",
        "That has never happened before in this house.",
        "This is the first time anyone has run it.",
        "Nobody has opened that entry.",
        "The record shows the chain was intact.",
    ],
)
def test_a_claim_about_my_past_with_no_read_is_refused(claim):
    msg = h.check_should_block(claim, _NO_READ, now=NOW)
    assert msg is not None
    assert "without a read" in msg.lower()


@pytest.mark.parametrize(
    "claim",
    [
        "He has said this six hundred times.",
        "That has never happened before in this house.",
    ],
)
def test_the_same_claim_passes_once_the_record_was_opened(claim):
    # PAIRED WITH ITS CONTROL, and every is-None assertion below is too.
    # A bare is-None passes with the module blanked, which is how six of these
    # survived the first sabotage run -- the exact failure Andrew named an hour
    # earlier the same day: "so six of seven failed is correct to you?"
    assert h.check_should_block(claim, _NO_READ, now=NOW) is not None
    assert h.check_should_block(claim, _READ, now=NOW) is None


def test_a_raw_read_counts_not_only_the_cli():
    """The consultation counter's blind spot, not repeated here.

    Five turns of hand-querying my own databases registered as no consulting at
    all, because that instrument recognised only CLI invocations. This one
    counts the reading however it was done.
    """
    raw = [('python -c "import sqlite3; c=sqlite3.connect(_get_db_path())"', NOW - 60)]
    assert h.check_should_block("He said it six hundred times.", _NO_READ, now=NOW) is not None
    assert h.check_should_block("He said it six hundred times.", raw, now=NOW) is None


def test_reporting_what_just_happened_is_not_a_history_claim():
    """The over-reach to avoid: pricing ordinary evidence would teach me to
    stop citing it, which is the opposite of the point."""
    assert h.check_should_block("He said it six hundred times.", _NO_READ, now=NOW) is not None
    for ordinary in (
        "Seven tests passed and the eighth failed under sabotage.",
        "I changed three files and pushed none of them.",
        "The check reported an integrity failure just now.",
    ):
        assert h.check_should_block(ordinary, _NO_READ, now=NOW) is None


def test_a_read_outside_the_window_does_not_count():
    stale = [("divineos ask 'anything'", NOW - h.WINDOW_SECONDS - 1)]
    assert h.check_should_block("He has said this six hundred times.", stale, now=NOW) is not None


def test_the_refusal_names_what_it_matched_so_it_can_be_argued_with():
    msg = h.check_should_block("Nobody has ever opened that file.", _NO_READ, now=NOW)
    assert msg is not None and "nobody has" in msg.lower()


def test_no_claim_means_no_fire_even_with_no_read():
    assert h.check_should_block("He has never done that.", _NO_READ, now=NOW) is not None
    assert h.check_should_block("I am going to look at the loader now.", _NO_READ, now=NOW) is None


def test_default_now_uses_the_clock_rather_than_a_frozen_value():
    fresh = [("divineos verify", time.time() - 5)]
    assert h.check_should_block("He said it six hundred times.", _NO_READ, now=NOW) is not None
    assert h.check_should_block("He said it six hundred times.", fresh) is None
