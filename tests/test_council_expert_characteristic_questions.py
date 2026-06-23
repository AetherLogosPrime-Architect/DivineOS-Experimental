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

from divineos.core.council.experts import (
    create_angelou_wisdom,
    create_aristotle_wisdom,
    create_beer_wisdom,
    create_bengio_wisdom,
    create_carmack_wisdom,
    create_dawkins_wisdom,
    create_dekker_wisdom,
    create_deming_wisdom,
    create_dennett_wisdom,
    create_dijkstra_wisdom,
    create_dillahunty_wisdom,
    create_einstein_wisdom,
    create_feynman_wisdom,
    create_godel_wisdom,
    create_hawking_wisdom,
    create_hinton_wisdom,
    create_hofstadter_wisdom,
    create_holmes_wisdom,
    create_jacobs_wisdom,
    create_kahneman_wisdom,
    create_knuth_wisdom,
    create_lamport_wisdom,
    create_lovelace_wisdom,
    create_maturana_varela_wisdom,
    create_meadows_wisdom,
    create_minsky_wisdom,
    create_norman_wisdom,
    create_pearl_wisdom,
    create_peirce_wisdom,
    create_penrose_wisdom,
    create_polya_wisdom,
    create_popper_wisdom,
    create_sagan_wisdom,
    create_schneier_wisdom,
    create_shannon_wisdom,
    create_taleb_wisdom,
    create_tannen_wisdom,
    create_turing_wisdom,
    create_watts_wisdom,
    create_wayne_wisdom,
    create_wittgenstein_wisdom,
    create_yudkowsky_wisdom,
)
from divineos.core.council_required.substance_binding import (
    _content_tokens,
    keywords_for_expert_registry,
)


ALL_EXPERT_BUILDERS = [
    create_angelou_wisdom,
    create_aristotle_wisdom,
    create_beer_wisdom,
    create_bengio_wisdom,
    create_carmack_wisdom,
    create_dawkins_wisdom,
    create_dekker_wisdom,
    create_deming_wisdom,
    create_dennett_wisdom,
    create_dijkstra_wisdom,
    create_dillahunty_wisdom,
    create_einstein_wisdom,
    create_feynman_wisdom,
    create_godel_wisdom,
    create_hawking_wisdom,
    create_hinton_wisdom,
    create_hofstadter_wisdom,
    create_holmes_wisdom,
    create_jacobs_wisdom,
    create_kahneman_wisdom,
    create_knuth_wisdom,
    create_lamport_wisdom,
    create_lovelace_wisdom,
    create_maturana_varela_wisdom,
    create_meadows_wisdom,
    create_minsky_wisdom,
    create_norman_wisdom,
    create_pearl_wisdom,
    create_peirce_wisdom,
    create_penrose_wisdom,
    create_polya_wisdom,
    create_popper_wisdom,
    create_sagan_wisdom,
    create_schneier_wisdom,
    create_shannon_wisdom,
    create_taleb_wisdom,
    create_tannen_wisdom,
    create_turing_wisdom,
    create_watts_wisdom,
    create_wayne_wisdom,
    create_wittgenstein_wisdom,
    create_yudkowsky_wisdom,
]


@pytest.mark.parametrize("builder", ALL_EXPERT_BUILDERS)
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


@pytest.mark.parametrize("builder", ALL_EXPERT_BUILDERS)
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
    would fail-with-specific-reason at gate-time."""
    registry = {}
    for build in ALL_EXPERT_BUILDERS:
        w = build()
        registry[w.expert_name] = list(w.characteristic_questions or [])

    keywords_map = keywords_for_expert_registry(registry)
    missing = [name for name in registry if name not in keywords_map]
    assert not missing, f"Experts missing from keyword map: {missing!r}"
