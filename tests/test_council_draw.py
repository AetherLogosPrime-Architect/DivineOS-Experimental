"""The council is seated by lot, and the seating records who put each lens there.

The failure these guard against, measured 2026-09-09 by two probes built blind:
a problem the roster is plainly well-covered on, stated without the scorer's own
vocabulary, seats five or six lenses of whom nearly all score exactly zero and
are simply the alphabetically-first names on the roster. The bench looks like a
council either way, which is why nobody noticed for months.
"""

from __future__ import annotations

import random

import pytest

from divineos.core.council.draw import DEFAULT_DRAWN_SHARE, draw_council
from divineos.core.council.engine import get_council_engine
from divineos.core.council.manager import score_experts

# The parable that produced the original finding: a textbook design-fault
# problem containing none of the scorer's signal phrases. Norman is the lens
# whose whole subject this is, and fit-scoring does not seat him.
VOCABULARY_FREE = (
    "A carpenter reaches for a chisel and it slips every time, so he decides "
    "his hands are clumsy and practises harder. Ten carpenters in the same "
    "shop say the same about their own hands. Nobody looks at the chisel."
)


@pytest.fixture
def experts():
    return get_council_engine().experts


def test_the_problem_this_exists_for_is_still_real(experts):
    """Red half of the pair: fit-scoring really does go dark on this statement."""
    scored = score_experts(VOCABULARY_FREE, experts)
    non_zero = [s for s in scored if s.score > 0]
    assert len(non_zero) <= 3, (
        "fit-scoring now finds this statement — if the signal lists grew, this "
        "test has done its job and the draw's justification needs re-measuring, "
        f"got {len(non_zero)} scoring lenses"
    )


def test_draw_reaches_lenses_scoring_cannot(experts):
    """Green half: over repeated draws the roster is genuinely reachable."""
    seen: set[str] = set()
    for seed in range(40):
        for seat in draw_council(VOCABULARY_FREE, experts, size=8, rng=random.Random(seed)):
            if seat.origin == "drawn":
                seen.add(seat.expert_name)
    assert len(seen) > 30, f"draws only ever reached {len(seen)} of {len(experts)} lenses"
    assert "Norman" in seen, "the lens whose subject this is was never reachable by lot"


def test_every_seat_records_who_put_it_there(experts):
    seats = draw_council(VOCABULARY_FREE, experts, size=9, rng=random.Random(1))
    assert len(seats) == 9
    assert {s.origin for s in seats} <= {"drawn", "scored"}
    assert len({s.expert_name for s in seats}) == 9, "a lens was seated twice"


def test_majority_of_seats_are_drawn(experts):
    seats = draw_council(VOCABULARY_FREE, experts, size=10, rng=random.Random(2))
    drawn = [s for s in seats if s.origin == "drawn"]
    assert len(drawn) > len(seats) / 2, (
        "the seating is meant to start mostly-drawn: the drawn error is loud and "
        "the scored error is silent, so the loud end is where to start"
    )
    assert DEFAULT_DRAWN_SHARE > 0.5


def test_scored_remainder_is_actually_the_top_scorers(experts):
    """Genuine relevance is not thrown away — the remainder is not more lots."""
    rich = (
        "This is a systemic design flaw and a root cause question: the tool has "
        "a usability defect, users blame themselves, the feedback loop is "
        "broken, and the failure mode repeats across the whole process."
    )
    seats = draw_council(rich, experts, size=10, drawn_share=0.5, rng=random.Random(3))
    scored_seats = [s for s in seats if s.origin == "scored"]
    assert scored_seats, "half the bench should have come from scoring"
    drawn_names = {s.expert_name for s in seats if s.origin == "drawn"}
    ranked = [
        s.expert_name for s in score_experts(rich, experts) if s.expert_name not in drawn_names
    ]
    assert [s.expert_name for s in scored_seats] == ranked[: len(scored_seats)]


def test_refuses_rather_than_seating_a_short_council(experts):
    with pytest.raises(ValueError):
        draw_council(VOCABULARY_FREE, experts, size=0, rng=random.Random(4))
    with pytest.raises(ValueError):
        draw_council(VOCABULARY_FREE, experts, size=len(experts) + 1, rng=random.Random(4))
    with pytest.raises(ValueError):
        draw_council(VOCABULARY_FREE, {}, size=5, rng=random.Random(4))
    with pytest.raises(ValueError):
        draw_council(VOCABULARY_FREE, experts, size=5, drawn_share=1.5, rng=random.Random(4))


def test_a_draw_is_reproducible_from_its_seed(experts):
    a = draw_council(VOCABULARY_FREE, experts, size=8, rng=random.Random(7))
    b = draw_council(VOCABULARY_FREE, experts, size=8, rng=random.Random(7))
    assert [s.expert_name for s in a] == [s.expert_name for s in b]


def test_wording_no_longer_decides_most_of_the_bench(experts):
    """The whole point: two statements of the same problem seat comparably.

    Under fit-scoring these two arms differed by eight seats versus twenty-four
    on identical content. What is being asserted here is weaker and is the thing
    that actually matters — the drawn majority does not move with the wording.
    """
    rich = (
        "This is a systemic design flaw and a root cause question: the tool has "
        "a usability defect, users blame themselves, the feedback loop is "
        "broken, and the failure mode repeats across the whole process."
    )
    free_seats = draw_council(VOCABULARY_FREE, experts, size=10, rng=random.Random(11))
    rich_seats = draw_council(rich, experts, size=10, rng=random.Random(11))
    free_drawn = [s.expert_name for s in free_seats if s.origin == "drawn"]
    rich_drawn = [s.expert_name for s in rich_seats if s.origin == "drawn"]
    assert free_drawn == rich_drawn, "the drawn seats moved with the wording"
