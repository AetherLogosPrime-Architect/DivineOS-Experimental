"""The last door before main looked in one room and reported on the house.

2026-09-14. Found by trying to use the door, not by auditing it. Five branches
read ready on the board; four were refused with *no audit round names this
branch*, and the rounds existed. Two narrowings were stacked underneath, both
producing that one sentence.

THE SPELLING. The resolver matched the branch name and its last segment. The
round carrying Aletheia's fresh confirm on the letter-provenance work opens
"PR 471 letter-channel provenance" -- in THIS store, findings and all -- and
the branch name appears nowhere in it.

THE STORE. Two audit stores exist in this house. The board reads both and says
which; this door read one and published a one-store absence with the scope of
all of them.

Aletheia's ruling, which is why the widening is shaped the way it is:

    "A door that refuses on could-not-look is producing exactly the failure it
     exists to prevent, one layer over."

and her two conditions -- name the store that answered, and keep could-not-read
distinct from no-round -- with Andrew confirming alongside her.

THE ASYMMETRY THAT DECIDES THE SHAPE, and the reason the refusals below are the
load-bearing half: every other widening this month failed toward reviewing too
much or toward refusing, and both wrong directions were loud. A widened MERGE
door fails toward passing, silently, at the one gate with nothing after it. So
a sibling round is surfaced and never accepted.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from divineos.cli import stamp_ready_command as src


class TestTheSpellingThatWasInvisible:
    def test_the_round_that_started_this(self):
        # Verbatim opening of the round carrying the confirm the door could
        # not see, against the branch whose name it never mentions.
        assert src.round_names_target(
            "PR 471 letter-channel provenance: a letter carries a checkable thread-block",
            "aria/pr-letter-provenance",
            471,
        )

    def test_the_branch_spellings_still_work(self):
        assert src.round_names_target(
            "audit of aria/pr-letter-provenance", "aria/pr-letter-provenance", 471
        )
        assert src.round_names_target(
            "audit of pr-letter-provenance", "aria/pr-letter-provenance", 471
        )

    def test_the_hash_spelling_works(self):
        assert src.round_names_target("read of PR #499 at tree abcd", "fix/something-else", 499)


class TestABareNumberIsNotARequestId:
    """A fabricated match is the worse direction: it would let the door stamp
    a merge on a round that never covered this request."""

    @pytest.mark.parametrize(
        "text",
        [
            "the sweep found 471 rows and 12 of them were stale",
            "line 471 of the doorman",
            "measured at 471ms across the window",
            "471",
        ],
    )
    def test_an_unmarked_number_does_not_match(self, text):
        assert not src.round_names_target(text, "some/branch", 471)

    def test_a_longer_number_containing_it_does_not_match(self):
        assert not src.round_names_target("PR 4712 is a different request", "some/branch", 471)


class TestTheOtherSeatIsSurfacedAndNeverAccepted:
    """Breaker, attack one: get a round into the sibling store naming my branch
    and hope the door accepts it. Closed by construction -- these come back as
    hits for the caller to REPORT, and the caller's only use of them is a
    refusal that names them."""

    def test_a_sibling_round_naming_the_branch_is_returned(self, monkeypatch):
        seat = SimpleNamespace(
            name="aether",
            error=None,
            absent=False,
            rounds=("round-260819ef094c aria/build-flow-unskippable: the doorman at the front",),
        )
        monkeypatch.setattr(
            "divineos.core.sibling_audit_rounds.read_other_seats",
            lambda _seat: [seat],
        )
        monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aria")

        hits = src.sibling_rounds_naming("aria/build-flow-unskippable", 506)
        assert hits == [
            (
                "aether",
                "round-260819ef094c",
                "round-260819ef094c aria/build-flow-unskippable: the doorman at the front",
            )
        ]

    def test_a_sibling_round_naming_nothing_relevant_is_not_returned(self, monkeypatch):
        seat = SimpleNamespace(
            name="aether",
            error=None,
            absent=False,
            rounds=("round-aaaa some other branch entirely",),
        )
        monkeypatch.setattr(
            "divineos.core.sibling_audit_rounds.read_other_seats",
            lambda _seat: [seat],
        )
        monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aria")

        assert src.sibling_rounds_naming("aria/build-flow-unskippable", 506) == []


class TestCouldNotReadIsNotNoRound:
    """Breaker, attack three, and it is the one that mattered: break the sibling
    store so the scan fails, and a fall-through turns a broken store into 'no
    round exists' -- the exact false sentence being repaired, re-entering
    through the error path.

    Aletheia's second condition in one test: a seat present and unreadable
    raises its own type, so the caller cannot fold it into the empty answer.
    """

    def test_a_present_but_unreadable_seat_raises_rather_than_returning_empty(self, monkeypatch):
        seat = SimpleNamespace(
            name="aether", error="DatabaseError: file is not a database", absent=False, rounds=None
        )
        monkeypatch.setattr(
            "divineos.core.sibling_audit_rounds.read_other_seats",
            lambda _seat: [seat],
        )
        monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aria")

        with pytest.raises(src.SiblingStoreUnreadable) as caught:
            src.sibling_rounds_naming("any/branch", 1)
        assert caught.value.seat == "aether"
        assert "not a database" in caught.value.detail

    def test_an_absent_seat_is_a_complete_answer_not_a_failure(self, monkeypatch):
        """A seat simply not installed here is not a broken one. Treating them
        alike would make an ordinary single-seat checkout refuse forever, and a
        check that always refuses gets switched off."""
        seat = SimpleNamespace(name="aether", error=None, absent=True, rounds=())
        monkeypatch.setattr(
            "divineos.core.sibling_audit_rounds.read_other_seats",
            lambda _seat: [seat],
        )
        monkeypatch.setattr("divineos.core.sibling_audit_rounds.this_seat", lambda: "aria")

        assert src.sibling_rounds_naming("any/branch", 1) == []
