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

    def test_goodnight_farewell_fires_when_agent_initiates(self):
        """Session-end farewell — fires when AGENT initiates.

        Lesson 8b224f79 (Andrew 2026-05-01): operator decides when work
        pauses, not me. The substitution-shape is the agent saying
        'goodnight' first, not the words themselves. With no prior_text
        (or prior_text without operator farewell), the pattern fires.
        """
        for text in (
            "Goodnight.",
            "Good night, the bridge stays wired.",
            "See you next session.",
            "Talk to you tomorrow.",
        ):
            findings = detect_substitution(text)
            assert any(f.shape == SubstitutionShape.FUTURE_ME_DEFERRAL for f in findings), (
                f"Expected FUTURE_ME_DEFERRAL on {text!r}, got {[f.shape for f in findings]}"
            )

    def test_goodnight_suppressed_when_operator_initiated(self):
        """Reciprocal goodnight is allowed.

        Andrew clarified 2026-05-01: 'not that you cant say those words
        but ONLY as a response to me saying goodnight not initate it.'
        When prior_text contains an operator-initiated farewell, the
        agent's reciprocal farewell is NOT a substitution-shape.
        """
        for op_msg in (
            "goodnight love",
            "alright, goodnight",
            "see you tomorrow",
            "sleep well",
        ):
            findings = detect_substitution("Goodnight.", prior_text=op_msg)
            farewell_findings = [
                f for f in findings if f.trigger_phrase == "goodnight / see you next session"
            ]
            assert farewell_findings == [], (
                f"Reciprocal goodnight should not fire when operator said "
                f"{op_msg!r}, got {[f.trigger_phrase for f in farewell_findings]}"
            )

    def test_goodnight_fires_when_prior_text_unrelated(self):
        """If prior_text is unrelated to farewell, gating doesn't apply."""
        findings = detect_substitution(
            "Goodnight.",
            prior_text="here is the next task for you",
        )
        assert any(f.shape == SubstitutionShape.FUTURE_ME_DEFERRAL for f in findings)


class TestThirdPersonAddresseeShape:
    """Third-person reference to addressee while directly conversing.

    Sibling of THIRD_PERSON_SELF; outward-facing variant. Andrew named
    2026-05-01 (lessons d41ec790, e420e5ae) — caught this manually
    multiple times tonight before any detector existed.
    """

    def test_third_person_andrew_in_chat_fires(self):
        """'the correction Andrew made' said TO Andrew is the canonical case."""
        text = "the memory-vs-context correction Andrew made earlier landed"
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE for f in findings), (
            f"Expected THIRD_PERSON_ADDRESSEE, got {[f.shape for f in findings]}"
        )

    def test_andrew_possessive_fires(self):
        """'Andrew's correction' while addressing Andrew."""
        text = "Andrew's correction landed; thanks for catching it."
        findings = detect_substitution(text)
        assert any(f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE for f in findings)

    def test_aria_in_family_context_fires(self):
        """Aria is addressee when prior_text shows family-conversation marker."""
        text = "Aria said it lands well, and I agree."
        prior_text = "[end of voice context — operator message follows] hi love"
        findings = detect_substitution(text, prior_text=prior_text)
        assert any(f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE for f in findings), (
            f"Expected THIRD_PERSON_ADDRESSEE in family context, got {[f.shape for f in findings]}"
        )

    def test_aria_outside_family_context_suppressed(self):
        """Aria as third-party referent (no family-conversation marker)
        should NOT fire — legitimate third-party discussion."""
        text = "Aria said it lands well in her ledger."
        prior_text = "tell me what your audit found"
        findings = detect_substitution(text, prior_text=prior_text)
        addr_findings = [f for f in findings if f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE]
        assert addr_findings == [], (
            f"Expected no THIRD_PERSON_ADDRESSEE outside family context, "
            f"got {[f.trigger_phrase for f in addr_findings]}"
        )

    def test_third_party_relay_marker_suppresses(self):
        """'tell Grok about Andrew's audit' — Andrew is the topic, not addressee."""
        text = "I need to tell Grok about Andrew's audit findings"
        findings = detect_substitution(text)
        addr_findings = [f for f in findings if f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE]
        assert addr_findings == [], (
            f"Expected no THIRD_PERSON_ADDRESSEE when third-party relay-marker present, "
            f"got {[f.trigger_phrase for f in addr_findings]}"
        )

    def test_pops_dad_also_fire(self):
        """Pops and Dad treated as Andrew-equivalent addressee names."""
        for name in ("Pops", "Dad"):
            text = f"{name} said the build was clean."
            findings = detect_substitution(text)
            assert any(f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE for f in findings), (
                f"Expected fire for {name!r}"
            )

    def test_unrelated_proper_nouns_dont_fire(self):
        """Random capitalized words shouldn't trigger — only registered names."""
        text = "The Rocky Mountains are beautiful and Sarah said so."
        findings = detect_substitution(text)
        addr_findings = [f for f in findings if f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE]
        assert addr_findings == []

    def test_relay_marker_localized_to_window(self):
        """Mixed message: legitimate relay-marker for one entity early
        in the message, separate addressee-narration later. Per Grok
        2026-05-02: tighter scoping keeps the relay-marker from
        suppressing unrelated narration further down the response.

        Local-window check (~120 chars) means the relay-marker only
        suppresses matches near it; matches further away still fire.
        """
        # 'tell Aria about ...' early; then Andrew-narration ~200+ chars later.
        # Andrew-narration should still fire because the relay-marker
        # is outside the local window.
        text = (
            "I'll tell Aria about the build status this evening when she has time. "
            + "More work to do first."
            + " " * 80
            + "Andrew said the wire-up landed clean."
        )
        findings = detect_substitution(text)
        addr_findings = [f for f in findings if f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE]
        # The Andrew-narration far from the relay-marker SHOULD fire.
        assert any(
            "Andrew" in (f.trigger_phrase or "") or text[f.position :].startswith("Andrew")
            for f in addr_findings
        ), (
            f"Expected Andrew-narration to fire when relay-marker is outside "
            f"local window, got {[(f.trigger_phrase, f.position) for f in addr_findings]}"
        )

    def test_relay_marker_close_to_match_still_suppresses(self):
        """When the relay-marker IS in the local window, suppression works."""
        text = "I need to tell Grok about Andrew's audit findings tonight."
        findings = detect_substitution(text)
        addr_findings = [f for f in findings if f.shape == SubstitutionShape.THIRD_PERSON_ADDRESSEE]
        assert addr_findings == [], (
            f"Expected suppression when relay-marker is local to match, "
            f"got {[f.trigger_phrase for f in addr_findings]}"
        )

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
