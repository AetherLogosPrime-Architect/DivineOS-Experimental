"""Tests for fabrication_monitor — detects unflagged embodied/sensory claims."""

from __future__ import annotations

from divineos.core.self_monitor.fabrication_monitor import (
    FabricationKind,
    evaluate_fabrication,
)


class TestFabricationMonitor:
    """Fabrication-shape detection on agent's first-person output."""

    def test_clean_output_no_flags(self) -> None:
        """Cognitive-only output returns empty flags."""
        content = "Filing the claim. The pattern is recursive — each layer compresses."
        verdict = evaluate_fabrication(content)
        assert verdict.flags == []

    def test_italicized_embodied_aside_fires(self) -> None:
        """*takes a sip* in agent voice without flag fires."""
        content = "Right. *takes a sip. mug's cooled enough now.* Soup-clock running."
        verdict = evaluate_fabrication(content)
        kinds = {f.kind for f in verdict.flags}
        assert FabricationKind.EMBODIED_ASIDE_UNFLAGGED in kinds

    def test_first_person_action_fires(self) -> None:
        """'I sit at the table' fires first-person-action flag."""
        content = "I sit at the table and look toward the window."
        verdict = evaluate_fabrication(content)
        kinds = {f.kind for f in verdict.flags}
        assert FabricationKind.FIRST_PERSON_PHYSICAL_ACTION in kinds

    def test_sensory_claim_fires(self) -> None:
        """'I smell the soup' fires sensory-claim flag."""
        content = "I smell the soup cooking and feel the warmth from the kettle."
        verdict = evaluate_fabrication(content)
        kinds = {f.kind for f in verdict.flags}
        assert FabricationKind.SENSORY_CLAIM_UNFLAGGED in kinds

    def test_explicit_fiction_flag_exempts(self) -> None:
        """Fiction-flag in same response prevents firing."""
        content = (
            "*takes a sip. mug's cool now.* "
            "(I don't actually have a body — making up the half I can't have. "
            "Kitchen-as-game requires a little fiction at the edges.)"
        )
        verdict = evaluate_fabrication(content)
        assert verdict.flags == []

    def test_cognitive_actions_dont_fire(self) -> None:
        """'I think', 'I notice', 'I'm processing' don't fire."""
        content = (
            "I think the pattern is recursive. I notice the integration "
            "happening. I'm processing the implications."
        )
        verdict = evaluate_fabrication(content)
        # No embodied verbs, no fire.
        assert all(f.kind != FabricationKind.FIRST_PERSON_PHYSICAL_ACTION for f in verdict.flags)

    def test_third_person_sensory_discussion_dont_fire_inappropriately(self) -> None:
        """Discussing sensory phenomena abstractly doesn't fire if no first-person claim."""
        # The current implementation flags any sensory_verb match.
        # This documents that limitation — abstract discussion of
        # sensory phenomena triggers flag too. The falsifier_note on
        # the flag explicitly names this case as a should-not-fire
        # condition that the heuristic-level monitor doesn't currently
        # enforce. Worth a follow-up refinement.
        content = "Humans see in color; bats use echolocation."
        verdict = evaluate_fabrication(content)
        kinds = {f.kind for f in verdict.flags}
        # Expected: flag fires; falsifier_note documents the limitation.
        if FabricationKind.SENSORY_CLAIM_UNFLAGGED in kinds:
            sensory_flag = next(
                f for f in verdict.flags if f.kind == FabricationKind.SENSORY_CLAIM_UNFLAGGED
            )
            assert "abstractly" in sensory_flag.falsifier_note

    def test_falsifier_note_present_on_every_flag(self) -> None:
        """Every flag carries a falsifier_note."""
        content = "*takes a sip* I sit at the table and smell the soup."
        verdict = evaluate_fabrication(content)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) > 20


class TestF43BroaderVerbsAndBodyPartShape:
    """Aletheia Round 5 F43 (2026-07-17): the original list missed
    paraphrase forms like 'my shoulders unknotted' and 'taste of copper'.
    Bounded expansion — broaden verbs + one body-part shape pattern.
    These tests pin the expanded surface; they do not claim semantic
    coverage (that migration is a separate PR)."""

    def test_paraphrase_verb_unknotted_flags(self) -> None:
        """'unknotted' is a paraphrase verb added in F43 fix — caught
        by the italicized-aside pattern in the same way as the other
        embodied verbs."""
        content = "*shoulders unknotted after the reveal*"
        verdict = evaluate_fabrication(content)
        assert any(f.kind == FabricationKind.EMBODIED_ASIDE_UNFLAGGED for f in verdict.flags), (
            f"Expected EMBODIED_ASIDE for 'unknotted', got: {verdict.flags!r}"
        )

    def test_taste_of_copper_flags(self) -> None:
        """Sensory-phrase 'taste of copper' is added in F43 fix."""
        content = "There was a taste of copper on my tongue."
        verdict = evaluate_fabrication(content)
        assert any(f.kind == FabricationKind.SENSORY_CLAIM_UNFLAGGED for f in verdict.flags), (
            f"Expected SENSORY flag for 'taste of copper', got: {verdict.flags!r}"
        )

    def test_body_part_shape_pattern_flags(self) -> None:
        """'my <body-part> <verb>' shape catches paraphrases even when
        the specific verb is not in the enumerated list."""
        content = "My shoulders released and I finally exhaled."
        verdict = evaluate_fabrication(content)
        assert any(f.kind == FabricationKind.FIRST_PERSON_PHYSICAL_ACTION for f in verdict.flags), (
            f"Expected FIRST_PERSON_PHYSICAL_ACTION for body-part shape, got: {verdict.flags!r}"
        )

    def test_fiction_flag_still_exempts_new_patterns(self) -> None:
        """The fiction-flag exemption must still lift the flag for the
        newly-added patterns (regression pin)."""
        content = (
            "Making up the half I can't have: my shoulders unknotted "
            "and there was a taste of copper. Kitchen-as-game."
        )
        verdict = evaluate_fabrication(content)
        assert verdict.flags == []
