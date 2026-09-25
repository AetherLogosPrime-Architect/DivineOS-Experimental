"""Every lens the council can surface must also be walkable.

WHY THIS EXISTS. On 2026-08-29 the council manager surfaced Feathers as a
relevant lens for a real problem, and `divineos council walk --lens Feathers`
refused it: *"not a registered council expert (or has no characteristic
questions)"*. It was registered. It had characteristic questions. Both halves
of the refusal were false.

The cause was a second copy of one fact. The walk command built its keyword map
from a hand-maintained roster -- ninety lines of import names that had to track
the engine's registrations by hand -- and the two had drifted. Engine:
forty-five. Roster: forty-two. Feathers, Foucault and Hoare were surfaceable and
unwalkable, which means the gate that requires a walk as evidence could never be
satisfied for them.

Two of the three had been surfaced in a fifteen-lens walk earlier that same day.
Their findings went into prose and could never have been recorded as evidence,
so a walk that felt complete was structurally incomplete and nothing said so.

THE TEST IS THE PROPERTY, NOT THE INSTANCE. It does not check that those three
names are present -- that would pass again the moment a forty-sixth expert is
added and forgotten. It checks that the two sets are equal, which is the thing
that must stay true.
"""

from __future__ import annotations

from divineos.cli.council_required_commands import _load_expert_keywords
from divineos.core.council.engine import CouncilEngine, _register_all_experts


def _registered_lens_names() -> set[str]:
    engine = CouncilEngine()
    _register_all_experts(engine)
    return {name.lower() for name in engine.list_experts()}


def test_every_registered_expert_is_walkable():
    """No expert may be surfaceable-but-unwalkable.

    Reported as a set difference rather than a count, so the failure names the
    lenses rather than only saying the numbers disagree -- a count would have
    told me three were missing without telling me which, and I would have had
    to go find them.
    """
    registered = _registered_lens_names()
    walkable = set(_load_expert_keywords())
    assert not (registered - walkable), (
        f"registered but NOT walkable: {sorted(registered - walkable)}"
    )


def test_no_walkable_lens_is_unregistered():
    """The other direction, so the assertion above is not half a check.

    A keyword map that grew a name the engine does not register would let a
    walk be recorded against a lens that cannot be surfaced -- evidence for a
    consultation that could never have happened.
    """
    registered = _registered_lens_names()
    walkable = set(_load_expert_keywords())
    assert not (walkable - registered), (
        f"walkable but NOT registered: {sorted(walkable - registered)}"
    )


def test_the_sets_are_not_both_empty():
    """Guard the guard.

    Two empty sets satisfy both assertions above perfectly. If the engine ever
    fails to register or the loader returns nothing, these tests would go green
    on a system where no lens can be walked at all -- which is the exact
    could-not-look-reading-as-all-clear shape this file is about.
    """
    assert len(_registered_lens_names()) >= 40
    assert len(_load_expert_keywords()) >= 40


def test_every_walkable_lens_carries_keywords():
    """A lens with an empty keyword set cannot pass substance-binding.

    It would be walkable in name and unwalkable in practice -- the same
    silence, one layer down, and the refusal message already conflates that
    case with being unregistered.
    """
    empty = sorted(name for name, kws in _load_expert_keywords().items() if not kws)
    assert not empty, f"walkable lenses with no keywords to bind against: {empty}"
