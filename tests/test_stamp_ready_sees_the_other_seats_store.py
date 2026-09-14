"""A refusal must not report an absence it was not in a position to see.

MEASURED 2026-09-10, chasing Andrew's question: *"you need to fix the root
cause of why you skipped those 3 build flow steps."*

The chain, each link checked rather than argued:

The three stations skipped — threadwalk, sabotage, second council — live on
the half of the build flow that only exists once a work item is open. The
doorman that forces one open at the first code edit is written, wired and
tested, and is not installed on this branch: the module file is absent and the
hook is not in this checkout's wiring. It is not installed because its pull
request is still a draft. It is a draft because clearing the draft flag needs
an audit round naming its branch, and ``stamp-ready`` said there was none.

There were two, in Aria's store, both naming the branch. The readiness board
reads the union of every seat and had been printing READY for that door.
``stamp-ready`` reads one store, found nothing, and said *No audit round names
branch ...* — a true statement about one store, published with the scope of
all of them.

So a door built to stop exactly this kind of skipping was itself held shut by
an instrument overstating the reach of its own search.

These tests hand the function fake seats rather than building a real sibling
checkout, because the subject is what it does with what the reader gives it —
present, absent, or unreadable — and a real second seat could only exercise
whichever of those three this machine happens to be in. The reader's own
behaviour across those states is covered by tests/test_sibling_audit_rounds.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from divineos.cli import stamp_ready_command as src


@dataclass
class _Seat:
    name: str
    rounds: tuple[str, ...] | None = ()
    absent: bool = False
    error: str | None = None


BRANCH = "build/work-item-doorman"
HER_ROUND = (
    "round-ea82c8d54d41 PR #505 build/work-item-doorman: the build-flow doorman "
    "at the reach. The refusal opens the work item."
)


def _seats(monkeypatch, seats):
    import divineos.core.sibling_audit_rounds as sar

    monkeypatch.setattr(sar, "this_seat", lambda: "aether")
    monkeypatch.setattr(sar, "read_other_seats", lambda _self: seats)


def test_a_round_in_her_store_is_found_and_named(monkeypatch):
    """The live case. Two of these existed while the refusal said none did."""
    _seats(monkeypatch, [_Seat("aria", rounds=(HER_ROUND,))])
    found, unreadable = src.sibling_rounds_naming(BRANCH)
    assert len(found) == 1
    assert "aria" in found[0]
    assert "round-ea82c8d54d41" in found[0]
    assert unreadable == []


def test_an_unrelated_round_is_not_a_match(monkeypatch):
    """The search must not become so eager that any round satisfies it."""
    _seats(
        monkeypatch,
        [_Seat("aria", rounds=("round-999 PR #123 some/other-branch: unrelated",))],
    )
    found, unreadable = src.sibling_rounds_naming(BRANCH)
    assert found == []
    assert unreadable == []


def test_a_seat_that_is_simply_not_here_is_not_an_error(monkeypatch):
    """An absent seat is a complete answer about an absent seat."""
    _seats(monkeypatch, [_Seat("aria", absent=True, rounds=None)])
    found, unreadable = src.sibling_rounds_naming(BRANCH)
    assert found == []
    assert unreadable == []


def test_an_unreadable_seat_is_reported_and_never_read_as_none(monkeypatch):
    """Could-not-look is not found-nothing — the whole point of the repair."""
    _seats(monkeypatch, [_Seat("aria", error="database is locked", rounds=None)])
    found, unreadable = src.sibling_rounds_naming(BRANCH)
    assert found == []
    assert len(unreadable) == 1
    assert "database is locked" in unreadable[0]


def test_a_broken_seat_reader_reports_rather_than_claiming_nothing(monkeypatch):
    """If the reader itself throws, that is unknown, not empty."""
    import divineos.core.sibling_audit_rounds as sar

    def _boom(_self):
        raise RuntimeError("seat index corrupt")

    monkeypatch.setattr(sar, "this_seat", lambda: "aether")
    monkeypatch.setattr(sar, "read_other_seats", _boom)
    found, unreadable = src.sibling_rounds_naming(BRANCH)
    assert found == []
    assert unreadable and "seat index corrupt" in unreadable[0]


def test_the_branch_tail_also_matches(monkeypatch):
    """Some rounds name only the branch's last segment.

    The readiness board matches on both, and two instruments disagreeing about
    what counts as naming a branch is how this whole thing started.
    """
    _seats(
        monkeypatch,
        [_Seat("aria", rounds=("round-abc work-item-doorman at tree 0a369f65",))],
    )
    found, _ = src.sibling_rounds_naming(BRANCH)
    assert len(found) == 1


@pytest.mark.parametrize("branch", ["", None])
def test_no_branch_means_no_claim_either_way(monkeypatch, branch):
    _seats(monkeypatch, [_Seat("aria", rounds=(HER_ROUND,))])
    found, unreadable = src.sibling_rounds_naming(branch or "")
    assert found == []
    assert unreadable == []


def test_it_does_not_hand_back_something_stampable(monkeypatch):
    """Guard against the fix growing teeth it must not have.

    A sibling round cannot be validated here — the validator reads confirms out
    of the local store by id, so a round this seat cannot open is a round whose
    two CONFIRMS it cannot check. This returns TEXT for a person to read, never
    a round object something downstream could stamp from.
    """
    _seats(monkeypatch, [_Seat("aria", rounds=(HER_ROUND,))])
    found, _ = src.sibling_rounds_naming(BRANCH)
    assert all(isinstance(item, str) for item in found)
