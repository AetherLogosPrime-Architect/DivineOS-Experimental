"""Pin the invariant: every registered council expert has at least one
non-empty characteristic_question populated.

Per Aether's 2026-06-22 peer-review Catch 1 on the council-required
enforcement design (prereg-3fbddd75fc16): the substance-binding gate's
lens-keyword cross-reference check looks up content-words from each
lens's characteristic_questions field. If any registered expert has an
empty/missing characteristic_questions list, the check NEVER passes
for that lens — accidentally narrowing the acceptable lens set and
producing a confusing "lens not registered" failure for what is
actually a population gap in the expert library.

This test fails loudly the moment that invariant breaks, so the
council-required gate's substance-binding stays trustworthy.
"""

from __future__ import annotations

import pytest

from divineos.core.council_required.substance_binding import (
    _content_tokens,
    keywords_for_expert_registry,
)


# DERIVED FROM THE ENGINE, NEVER RETYPED.
#
# This was a hand-written roster of forty-two, and the engine had grown to
# forty-five. Three experts -- Feathers, Foucault and Hoare -- were registered,
# surfaceable by the council chamber, and absent from this list, so the
# invariant this file exists to pin was never checked for any of them.
#
# The sharp part is above, in the docstring: it names that exact failure --
# "a confusing 'lens not registered' failure for what is actually a population
# gap in the expert library" -- and it could not see the gap, because it
# enumerated its own copy of the thing it was guarding.
#
# The walk command was repaired this way on 2026-08-28 and this third copy was
# missed. Same engine, same public accessors, so the two can no longer drift
# apart: adding an expert makes it tested here without a second step.
def _experts_from_the_engine():
    from divineos.core.council.engine import CouncilEngine, _register_all_experts

    engine = CouncilEngine()
    _register_all_experts(engine)
    return [engine.get_expert(name) for name in engine.list_experts()]


# EACH CASE CARRIES ITS EXPERT'S NAME. The first version parametrised over bare
# lambdas, and pytest labelled the cases builder0 through builder44 -- so a
# failure would have said an expert was broken without saying which one. A test
# whose failure cannot be read is half a test, which is the same shape as an
# instrument whose silence cannot be read.
_EXPERTS = _experts_from_the_engine()

# Plain callables for the tests that walk the list themselves.
ALL_EXPERT_BUILDERS = [(lambda w=w: w) for w in _EXPERTS]

# The same set, labelled, for the parametrised cases.
NAMED_EXPERT_BUILDERS = [pytest.param((lambda w=w: w), id=w.expert_name) for w in _EXPERTS]


@pytest.mark.parametrize("builder", NAMED_EXPERT_BUILDERS)
def test_expert_has_characteristic_questions(builder):
    """Each registered expert must declare at least one
    characteristic_question, otherwise the council-required gate
    cannot keyword-cross-reference findings for that lens."""
    wisdom = builder()
    assert wisdom.characteristic_questions, (
        f"Expert {wisdom.expert_name!r} has no characteristic_questions"
    )
    assert any((q or "").strip() for q in wisdom.characteristic_questions), (
        f"Expert {wisdom.expert_name!r} has only empty characteristic_questions"
    )


@pytest.mark.parametrize("builder", NAMED_EXPERT_BUILDERS)
def test_expert_characteristic_questions_have_content_tokens(builder):
    """Each registered expert must declare characteristic_questions whose
    combined text produces at least one substantive content-token after
    stopword filtering. A lens whose questions tokenize to only stopwords
    cannot satisfy the keyword cross-reference check."""
    wisdom = builder()
    all_text = " ".join(wisdom.characteristic_questions or [])
    tokens = _content_tokens(all_text)
    assert tokens, f"Expert {wisdom.expert_name!r} characteristic_questions yield no content-tokens"


def test_keywords_for_expert_registry_covers_all_experts():
    """Build the lens-keyword map the gate uses and verify every
    registered expert lands in the map. A lens missing from the map
    would fail-with-specific-reason at gate-time.

    2026-07-07 case-normalization: keywords_for_expert_registry stores
    keys lowercase so lookups are case-insensitive (CLI users type
    'schneier'; registry stores 'Schneier'). This assertion lowercases
    the check to match the new contract.
    """
    registry = {}
    for build in ALL_EXPERT_BUILDERS:
        w = build()
        registry[w.expert_name] = list(w.characteristic_questions or [])

    keywords_map = keywords_for_expert_registry(registry)
    missing = [name for name in registry if name.lower() not in keywords_map]
    assert not missing, f"Experts missing from keyword map: {missing!r}"


def test_keywords_for_expert_registry_stores_keys_lowercase():
    """Pin the case-normalization invariant introduced 2026-07-07.

    Registry keys are stored lowercase in the returned map so lookups
    at check-time can normalize the incoming lens name (which may come
    from CLI input in any case) and still hit the registered lens.
    Without this normalization, `--lenses "schneier"` misses `Schneier`
    and the substance-binding check falsely reports the empty-registry
    error — the exact drift caught in the 2026-07-07 audit.
    """
    registry = {"Schneier": ["What is the threat model here?"]}
    keywords_map = keywords_for_expert_registry(registry)
    assert "schneier" in keywords_map
    assert "Schneier" not in keywords_map, (
        "Capital-cased key leaked through — case-normalization broken"
    )
