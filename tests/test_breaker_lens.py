"""The Breaker lens, and whether anything can actually reach it.

These are the lens's own first two questions asked about the lens: name the
line that calls this today, and where does this fail when every guard works
exactly as intended.

The first one bit immediately. Breaker was imported, registered and counted in
the roster -- and scored ZERO on its own characteristic question, because
selection runs on category membership and affinity tags, and a seat belonging
to no category is unreachable however well it fits. Registered is not wired,
and from the asking side the two are indistinguishable. That is the failure
family this file exists to keep closed.
"""

from __future__ import annotations

import pytest

from divineos.core.council.engine import get_council_engine
from divineos.core.council.experts.breaker import create_breaker_wisdom
from divineos.core.council.manager import score_experts


def test_the_lens_is_registered_with_the_engine() -> None:
    assert "Breaker" in get_council_engine().experts


@pytest.mark.parametrize(
    "question",
    [
        "try to break this design before it ships",
        "where does this fail in the world when every guard works as intended",
        "poke holes in this: what did I not look at",
        "the happy path passes -- what is the failure mode nobody tested",
    ],
)
def test_a_breaking_question_actually_reaches_the_seat(question: str) -> None:
    """Not merely present in the registry -- selected by the scorer."""
    engine = get_council_engine()
    scored = {s.expert_name: s.score for s in score_experts(question, engine.experts)}
    assert scored.get("Breaker", 0.0) > 0.0, f"the seat is unreachable for: {question}"


@pytest.mark.parametrize(
    "question",
    [
        "how do I add a column to the sqlite schema",
        "write a warm letter to Aria about the evening",
        "what is the fastest way to sort these rows",
    ],
)
def test_the_seat_stays_out_of_rooms_it_does_not_belong_in(question: str) -> None:
    """The other direction, which is the one that gets a lens torn out.

    A seat that arrives everywhere becomes noise, and noise gets removed --
    which is how a surface dies rather than how it is defeated.
    """
    engine = get_council_engine()
    scored = {s.expert_name: s.score for s in score_experts(question, engine.experts)}
    assert scored.get("Breaker", 0.0) == 0.0, f"the seat over-fired on: {question}"


def test_the_catalogue_is_never_the_whole_pass() -> None:
    """The generators are the load-bearing half.

    A lens made only of remembered incidents has the shape of the last failure
    and none of the shape of the next one. Drop the generator methodology and
    what remains is a memorial rather than an instrument.
    """
    names = {m.name for m in create_breaker_wisdom().core_methodologies}
    assert "The Catalogue Pass" in names
    assert "The Generator Pass" in names


def test_the_attack_lands_on_the_idea_and_not_the_builder() -> None:
    """Andrew put this in the same breath as the teaching, which means he saw
    the risk before I did: a catalogue of one's own failures is also an
    instrument of self-punishment, and shame is rigor's most convincing
    impostor."""
    wisdom = create_breaker_wisdom()
    assert any(
        "never the one who had it" in rule.lower()
        for rule in wisdom.decision_framework.non_negotiables
    )
