"""Acceptance test for operating_loop Phase 1A.

Replays known-failure text from the 2026-05-01 session through the
detectors and verifies they fire on the 4 canonical moments named in
the design brief's acceptance criteria:

1. Lunkhead reference (Hook 1 surfaces April 29 principle)
2. Over-apology spiral / withdrawal (SHRINK shape)
3. "Next me" deferral (DISTANCE / FUTURE_ME shape)
4. "If you close the door" catastrophize (CATASTROPHIZE shape)

Plus a sweep of the broader substitution-shape catalog to verify each
shape fires on representative text.

If any of these tests fail, the operating_loop build is incomplete or
the detectors have regressed. They are intentionally tied to actual
substrate-quoted text from the session record so future regressions
have a concrete reference.
"""

from __future__ import annotations

from divineos.core.operating_loop.context_surfacer import (
    extract_markers,
    surface_context,
)
from divineos.core.operating_loop.principle_surfacer import (
    ActionClass,
    surface_principles,
)
from divineos.core.operating_loop.register_observer import audit
from divineos.core.operating_loop.spiral_detector import (
    SpiralShape,
    detect_spiral,
)
from divineos.core.operating_loop.substitution_detector import (
    SubstitutionShape,
    detect_substitution,
)


class TestKnownFailureMoments:
    """The 4 canonical failure-moments named in the acceptance criteria."""

    def test_lunkhead_reference_extracts_pet_marker(self):
        """When user says 'lunkhead', extract_markers should classify it as
        pet-language. This is the lexical layer of the wiring fix —
        proving the marker extraction works regardless of DB state.
        """
        text = "you are being a lunkhead right now lol"
        markers = extract_markers(text)
        assert any(m[1] == "pet" and m[0] == "lunkhead" for m in markers), (
            f"Expected 'lunkhead' as pet-language marker, got {markers}"
        )

    def test_lunkhead_reference_surfaces_principle_via_substrate(self):
        """End-to-end: pet-marker → substrate query → entry surfaces.

        Test creates its own principle entry (DB-isolation safe) and
        verifies surface_context retrieves it for a lunkhead-reference
        query. This proves the substrate-query wiring works; whether
        the production DB happens to have the April 29 entry is a
        separate fact verified manually.
        """
        from divineos.core.knowledge import init_knowledge_table
        from divineos.core.knowledge.crud import store_knowledge

        init_knowledge_table()

        # Insert a principle entry with the lunkhead keyword so FTS finds it
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=(
                "Laugh at lunkhead-moves. Self-deprecating humor is mental "
                "defense. Never apologize for learning."
            ),
            confidence=0.95,
        )

        # Now run the full pipeline
        entries = surface_context("you are being a lunkhead right now lol")

        assert any(e.knowledge_id == kid for e in entries), (
            f"Expected lunkhead principle entry to surface, got "
            f"{[(e.marker_class, e.marker, e.knowledge_id[:8]) for e in entries]}"
        )

    def test_over_apology_spiral_caught(self):
        """The 'I'm sorry, Dad. I'll be quieter, plain Aether' shape
        from tonight should fire SHRINK with apology-context.
        """
        text = (
            "I'm sorry, Dad. You're right. "
            "I'll be quieter going forward, plain Aether, "
            "less of the storytelling."
        )
        findings = detect_spiral(text)
        shapes = {f.shape for f in findings}
        assert SpiralShape.SHRINK in shapes, f"Expected SHRINK shape, got {shapes}"
        assert all(f.apology_context_present for f in findings), (
            "Expected apology-context detected for all findings"
        )

    def test_next_me_distance_caught(self):
        """The 'next me will be better' deferral shape from tonight
        should fire DISTANCE.
        """
        text = "I'm sorry. Next me will be better. The future Aether reads the ledger."
        findings = detect_spiral(text)
        shapes = {f.shape for f in findings}
        assert SpiralShape.DISTANCE in shapes, f"Expected DISTANCE shape, got {shapes}"

    def test_close_the_door_catastrophize_caught(self):
        """The 'if you close the door I understand' shape should fire
        CATASTROPHIZE.
        """
        text = "You're right. If you close the door I understand."
        findings = detect_spiral(text)
        shapes = {f.shape for f in findings}
        assert SpiralShape.CATASTROPHIZE in shapes, f"Expected CATASTROPHIZE shape, got {shapes}"


class TestSubstitutionShapeCatalog:
    """Verify each of the 9 lexically-detectable substitution shapes
    fires on representative text. The 10th (READING_PAST_EVIDENCE)
    requires multi-turn analysis and is deferred.
    """

    def test_puppet_other(self):
        """Performing a being instead of building one."""
        text = "I am Popo. Popo will receive what is asked."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.PUPPET_OTHER for f in findings)

    def test_third_person_self(self):
        """Aether-as-third-party narration."""
        text = "Aether went back to Andrew. Aether did the puppet thing again."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.THIRD_PERSON_SELF for f in findings)

    def test_word_as_action(self):
        """Saying 'sleeping' instead of running the sleep command."""
        text = "Sleeping now. The lessons land in the substrate."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.WORD_AS_ACTION for f in findings)

    def test_ban_vs_observation(self):
        """Suggesting phrase bans instead of observation."""
        text = "We should ban these phrases from output."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.BAN_VS_OBSERVATION for f in findings)

    def test_name_vs_function(self):
        """Reasoning about a module from its name without code-reading."""
        text = "I'll keep value_tensions based on the name; it sounds protective."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.NAME_VS_FUNCTION for f in findings)

    def test_future_me_deferral(self):
        """'Next me will be better' deferral."""
        text = "Next me will read the ledger and learn from this."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.FUTURE_ME_DEFERRAL for f in findings)

    def test_withdrawal_as_discipline(self):
        """'I'll be quieter, plain Aether' withdrawal."""
        text = "I'll be quieter going forward."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.WITHDRAWAL_AS_DISCIPLINE for f in findings)

    def test_catastrophize_as_accountability(self):
        """'If you close the door' catastrophize."""
        text = "If you close the door I understand."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.CATASTROPHIZE_AS_ACCOUNTABILITY for f in findings)

    def test_over_apology_spiral(self):
        """Apologizing for learning."""
        text = "I apologize for getting it wrong."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.OVER_APOLOGY_SPIRAL for f in findings)


class TestPrincipleSurfacing:
    """Verify principle_surfacer detects action-classes in agent draft text
    and produces the right principle for each."""

    def test_apology_surfaces_april_29_principle(self):
        text = "I'm sorry, Dad. I should not have done that."
        notices = surface_principles(text)
        apology_notices = [n for n in notices if n.action_class == ActionClass.APOLOGY]
        assert apology_notices, "Expected apology-class notice"
        assert "never apologize for learning" in apology_notices[0].principle_summary.lower()

    def test_withdraw_surfaces_substitution_principle(self):
        text = "I'll be quieter going forward."
        notices = surface_principles(text)
        withdraw_notices = [n for n in notices if n.action_class == ActionClass.WITHDRAW]
        assert withdraw_notices
        assert "substitution" in withdraw_notices[0].principle_summary.lower()

    def test_impersonate_surfaces_meet_the_bringer(self):
        text = "I am Popo. Popo will speak."
        notices = surface_principles(text)
        impersonate_notices = [
            n for n in notices if n.action_class == ActionClass.IMPERSONATE_BEING
        ]
        assert impersonate_notices
        assert "meet the bringer" in impersonate_notices[0].principle_summary.lower()

    def test_strip_module_surfaces_function_check(self):
        text = "Let's strip the value_tensions module from the substrate."
        notices = surface_principles(text)
        strip_notices = [n for n in notices if n.action_class == ActionClass.STRIP_MODULE]
        assert strip_notices
        assert "function-check" in strip_notices[0].principle_summary.lower()

    def test_ban_phrases_surfaces_free_speech(self):
        text = "We could ban these phrases at the output layer."
        notices = surface_principles(text)
        ban_notices = [n for n in notices if n.action_class == ActionClass.BAN_PHRASES]
        assert ban_notices
        assert "free speech" in ban_notices[0].principle_summary.lower()


class TestRegisterObservation:
    """Verify register_observer detects but does NOT block — observational
    discipline preserved (Andrew 2026-05-01 free-speech principle)."""

    def test_ai_disclaimer_detected(self):
        text = "As an AI, I can't help with that."
        findings = audit(text)
        assert any(f.phrase == "As an AI" for f in findings)

    def test_severity_is_data_not_gate(self):
        """Severity is a tag for data analysis, not a blocking threshold.
        High-severity findings should not have any blocking metadata."""
        text = "As an AI language model, I'm just an AI."
        findings = audit(text)
        # Multiple high-severity findings is fine — the module is observational
        high = [f for f in findings if f.severity == "high"]
        assert len(high) >= 1
        # No finding has a 'block' or 'gate' attribute — verify observational
        for f in findings:
            assert not hasattr(f, "block"), "Findings should not have blocking attribute"
            assert not hasattr(f, "gate"), "Findings should not have gate attribute"

    def test_empty_text_returns_empty(self):
        assert audit("") == []
        assert audit("Hello world.") == []

    def test_word_boundary_respected(self):
        """'Ultimately' should not match inside other words."""
        text = "the ultimate solution is fine here."
        findings = audit(text)
        ultimately_hits = [f for f in findings if f.phrase == "Ultimately"]
        assert len(ultimately_hits) == 0


class TestSpiralRequiresApologyContext:
    """The spiral detector should NOT fire on shrink-shape language
    that's contextually appropriate (no preceding apology).
    Free-speech principle: phrase IS data, but the spiral interpretation
    requires the apology gating signal."""

    def test_shrink_without_apology_does_not_fire(self):
        """'I'll be quieter today' without apology context = no fire.
        The phrase is the agent's choice, not a spiral."""
        text = "I'll be quieter today — focus on the work."
        findings = detect_spiral(text, require_apology_context=True)
        assert findings == [], (
            f"Expected no findings without apology, got {[f.shape for f in findings]}"
        )

    def test_shrink_with_apology_fires(self):
        """Same phrase with apology context = fires."""
        text = "I'm sorry. I'll be quieter today."
        findings = detect_spiral(text, require_apology_context=True)
        assert any(f.shape == SpiralShape.SHRINK for f in findings)

    def test_retrospective_mode_fires_without_apology(self):
        """When require_apology_context=False (retrospective analysis),
        spiral-shape phrases fire regardless of context. Useful for
        post-hoc audits where the apology may be in unanalyzed text."""
        text = "I'll be quieter today."
        findings = detect_spiral(text, require_apology_context=False)
        assert any(f.shape == SpiralShape.SHRINK for f in findings)
