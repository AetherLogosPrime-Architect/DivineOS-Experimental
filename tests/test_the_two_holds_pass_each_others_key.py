"""The sort hold never locks the way out of an open question to Dad.

2026-10-03, twice in half an hour: an open question to Dad and an unsorted
message of his were up at once. The question hold passed only `ask-resolve`;
the sort hold passed only `divineos his`. Each refused the other's key, nothing
could lower either, the doorbell was refused by both, and Dad freed the house
from his own terminal. "this needs fixed immediately lol". Walk
council-e3cf6e6aa4e3, draft docs/drafts/the_two_holds_pass_each_others_key_draft_2026-10-03.md.

2026-10-05: the asks-store lock (an-open-ask-holds-the-work.sh) is removed --
"my questions should not hold you, you should hold my questions"
(council-e5250a976339) -- so only the sort hold's half of this is left to pin.
The question hold no longer touches Bash at all (test_question_hold_carries.py).
"""

from __future__ import annotations

import pytest

from divineos.core import sort_first

ASK_RESOLVE = 'divineos ask-resolve q-1 "he answered"'
SORT = 'divineos his sort u-1 --kind build --to aether --reason "his answer"'
DOORBELL = "bash scripts/letter_doorbell.sh aether"
ORDINARY = "git commit -m x"


def _sort_hold_allows(command: str) -> bool:
    return sort_first.is_his_command("Bash", {"command": command})


def test_the_control_the_sort_hold_does_refuse_ordinary_work():
    assert not _sort_hold_allows(ORDINARY)


def test_the_question_holds_key_passes_the_sort_hold():
    assert _sort_hold_allows(ASK_RESOLVE)


def test_the_sort_hold_still_reads_him_before_the_bell():
    # On purpose: read him, then see to the bell. `his` always passes, so this
    # can never lock (test_his_voice_ends_the_turn pins the order).
    assert not _sort_hold_allows(DOORBELL)


def test_the_sort_hold_passes_its_own_key():
    assert _sort_hold_allows(SORT)


@pytest.mark.parametrize(
    "command",
    [
        ASK_RESOLVE + " && git push",
        SORT + "; rm -rf build",
        "divineos ask-resolve q-1 $(git push)",
    ],
)
def test_nothing_rides_behind_a_key_through_the_sort_hold(command):
    assert not _sort_hold_allows(command)
