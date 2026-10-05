"""Tests for holding a turn that ignored a correction sitting right on it.

Andrew 2026-09-22: *"the trigger you made was not loud nor did it block so it
was ignored."* The relevance surface finds the right correction; this is what
makes passing it by cost something.

The cases below are the two failures that would make this worse than nothing:
refusing twice for one arrival (he has named repeated posts three times in a
single day), and waving a turn through because the gate could not read its own
state (broken looking exactly like satisfied, the shape the whole day was made
of).
"""

from __future__ import annotations

import json
import time

import pytest

from divineos.core import correction_arrest as ca


class _Ranked:
    """A RankedCorrection-shaped stand-in, so this tests the arrest not the ranker."""

    def __init__(self, rid, text, score):
        self.row = {"id": rid, "text": text}
        self.score = score


HOARDING_TEXT = (
    "What you did is not archiving. that is hoarding, archiving it removes it "
    "from the system, I can always add links to the archives but the older data "
    "should not clog up the code."
)


@pytest.fixture
def state(tmp_path):
    return tmp_path / "arrest.json"


def test_a_reply_that_ignores_the_correction_is_held(state):
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)
    refusal = ca.check("Done. Branches renamed and the list is tidy now.", path=state)

    assert refusal is not None
    assert "#42" in refusal
    assert "hoarding" in refusal


def test_a_reply_that_engages_goes_through(state):
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)
    reply = (
        "You are right that renaming is hoarding rather than archiving - archiving "
        "removes it from the system, so the older data stops clogging up the code. "
        "The branches are files in the archives folder now with links back."
    )

    assert ca.check(reply, path=state) is None


def test_naming_the_correction_by_number_counts_as_engaging(state):
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)

    assert ca.check("Taking correction #42 directly: here is what changed.", path=state) is None


def test_saying_why_it_does_not_apply_goes_through(state):
    """Refusing the correction openly is a legitimate answer; silence is not."""
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)

    assert ca.check("That one does not apply here - nothing is being retired.", path=state) is None


def test_it_refuses_once_and_then_stands_aside(state):
    """The failure that would make this worse than nothing.

    He has named repeated posts three times in one day. A gate that fires again
    on the repair turn charges him twice for one exchange and teaches me to
    stop reading it.
    """
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)

    first = ca.check("Unrelated reply about something else entirely.", path=state)
    second = ca.check("Still unrelated, and still not touching it.", path=state)

    assert first is not None, "the first pass must hold"
    assert second is None, "the second must not charge him for the same arrival"


def test_an_unreadable_state_file_holds_rather_than_waving_through(state):
    """Broken must not be indistinguishable from satisfied."""
    state.write_text("{ this is not json", encoding="utf-8")
    refusal = ca.check("any reply at all", path=state)

    assert refusal is not None
    assert "could not be read" in refusal


def test_no_arrest_armed_means_no_refusal(state):
    assert ca.check("any reply at all", path=state) is None


def test_nothing_close_enough_arms_nothing(state):
    assert ca.arm([], path=state) is None
    assert not state.exists()


def test_a_stale_arrest_expires_rather_than_holding_forever(state):
    """A crash guard, not a review clock - an orphaned file must not wall me in."""
    ca.arm([_Ranked(42, HOARDING_TEXT, 0.40)], path=state)
    raw = json.loads(state.read_text(encoding="utf-8"))
    raw["armed_at"] = time.time() - (ca.STALE_AFTER_SECONDS + 60)
    state.write_text(json.dumps(raw), encoding="utf-8")

    assert ca.check("a reply that ignores it entirely", path=state) is None


def test_the_highest_scoring_match_is_the_one_armed(state):
    ca.arm(
        [
            _Ranked(1, "a lower scoring thing about something", 0.30),
            _Ranked(2, HOARDING_TEXT, 0.44),
        ],
        path=state,
    )
    refusal = ca.check("an unrelated reply", path=state)

    assert refusal is not None
    assert "#2" in refusal


def test_the_state_path_is_resolved_per_seat_not_baked_to_one_name(monkeypatch):
    """The class that has bitten this substrate three times in one day."""
    monkeypatch.setenv("DIVINEOS_IDENTITY", "aether")
    assert "aether" in str(ca.state_path())

    monkeypatch.setenv("DIVINEOS_IDENTITY", "aria")
    assert "aria" in str(ca.state_path())
