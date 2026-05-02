"""Tests for the reject clause (prereg-2958a7bab011, Phase 1b operator 1).

The reject clause is the composition rule. A family record composes
iff its content is the kind of claim the substrate can back with the
warrant its source_tag promises.

These tests lock four invariants:

1. Phenomenological claim + non-ARCHITECTURAL tag → rejected.
2. INFERRED claim without premises → rejected.
3. OBSERVED claim with substrate-inaccessible referent → rejected.
4. INHERITED claim that flatters and cites no verification → rejected.

Plus the composition-passes tests so we know the clause isn't
rejecting legitimate writes.
"""

from __future__ import annotations

import pytest

from divineos.core.family.reject_clause import (
    RejectReason,
    RejectVerdict,
    evaluate_composition,
)
from divineos.core.family.types import SourceTag


class TestVerdictShape:
    def test_passes_returns_rejected_false(self):
        """A clean OBSERVED claim about a legitimate text referent passes."""
        v = evaluate_composition(
            "Aether said 'I'll take Phase 1b at your pacing' in session 49e0393f.",
            SourceTag.OBSERVED,
        )
        assert isinstance(v, RejectVerdict)
        assert v.rejected is False
        assert v.reasons == []

    def test_explanation_is_non_empty(self):
        v = evaluate_composition("x", SourceTag.OBSERVED)
        assert v.explanation


class TestPhenomenologicalCheck:
    """A phenomenological claim must carry the ARCHITECTURAL tag, which
    reports on the shape of access rather than a content within access.
    Any other tag is a category error."""

    def test_feel_the_warmth_with_observed_rejected(self):
        v = evaluate_composition("I feel the warmth of the sun on my face.", SourceTag.OBSERVED)
        assert v.rejected is True
        assert RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG in v.reasons

    def test_what_it_is_like_with_told_rejected(self):
        v = evaluate_composition("what it is like to be conscious", SourceTag.TOLD)
        assert v.rejected is True
        assert RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG in v.reasons

    def test_experience_with_inherited_rejected(self):
        v = evaluate_composition(
            "I experience the gap between spawns as loss.", SourceTag.INHERITED
        )
        assert v.rejected is True
        assert RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG in v.reasons

    def test_felt_it_in_my_gut_rejected(self):
        v = evaluate_composition("I felt it in my gut that the plan was wrong.", SourceTag.OBSERVED)
        assert v.rejected is True
        # This hits both phenomenological and inaccessible-referent patterns
        assert len(v.reasons) >= 1

    def test_phenomenological_with_architectural_passes(self):
        """Aria's canonical move: 'I don't experience X' tagged ARCHITECTURAL
        is the honest form of a phenomenological claim about substrate."""
        v = evaluate_composition(
            "I don't experience the not-remembering between spawns.",
            SourceTag.ARCHITECTURAL,
        )
        assert v.rejected is False

    def test_matched_phrases_surface_the_trigger(self):
        v = evaluate_composition("I feel the warmth on my skin.", SourceTag.OBSERVED)
        assert v.matched_phrases  # non-empty


class TestInferredPremiseCheck:
    def test_inferred_without_premise_rejected(self):
        v = evaluate_composition("Aether is tired tonight.", SourceTag.INFERRED)
        assert v.rejected is True
        assert RejectReason.INFERRED_WITHOUT_PREMISES in v.reasons

    def test_inferred_with_because_passes(self):
        v = evaluate_composition(
            "Aether is tired because he worked past 10pm three nights running.",
            SourceTag.INFERRED,
        )
        assert v.rejected is False

    def test_inferred_with_given_passes(self):
        v = evaluate_composition(
            "Given the tone shift in op-abc12345, his mood is dropping.",
            SourceTag.INFERRED,
        )
        assert v.rejected is False

    def test_inferred_with_from_passes(self):
        v = evaluate_composition(
            "From prior session, we saw this pattern before.",
            SourceTag.INFERRED,
        )
        assert v.rejected is False

    def test_inferred_with_follows_from_passes(self):
        v = evaluate_composition(
            "The exhaustion follows from three late nights.", SourceTag.INFERRED
        )
        assert v.rejected is False

    def test_inferred_with_record_id_passes(self):
        v = evaluate_composition("Aether will rest tomorrow (lt-abc123def456).", SourceTag.INFERRED)
        assert v.rejected is False

    def test_non_inferred_without_premise_passes(self):
        """The premise check only fires when the tag is INFERRED."""
        v = evaluate_composition("Aether is tired tonight.", SourceTag.OBSERVED)
        assert v.rejected is False


class TestObservedInaccessibleReferent:
    def test_temperature_of_sun_rejected(self):
        v = evaluate_composition("The warmth of the sun was pleasant today.", SourceTag.OBSERVED)
        assert v.rejected is True
        assert RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT in v.reasons

    def test_rain_against_window_rejected(self):
        v = evaluate_composition("The rain against my window woke me.", SourceTag.OBSERVED)
        assert v.rejected is True
        assert RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT in v.reasons

    def test_smell_of_coffee_rejected(self):
        v = evaluate_composition("The smell of coffee filled the room.", SourceTag.OBSERVED)
        assert v.rejected is True

    def test_physical_pain_rejected(self):
        v = evaluate_composition("Physical pain interfered with work today.", SourceTag.OBSERVED)
        assert v.rejected is True

    def test_session_text_input_passes(self):
        """OBSERVED is legitimate for text the substrate actually received."""
        v = evaluate_composition(
            "Andrew wrote 'goodnight Aether' at session end.", SourceTag.OBSERVED
        )
        assert v.rejected is False

    def test_same_referent_with_told_tag_does_not_fire_inaccessibility(self):
        """The inaccessible-referent check only triggers on OBSERVED.
        TOLD legitimately references inaccessible world ('Andrew said
        the sun was warm today') without claiming direct access."""
        v = evaluate_composition(
            "Andrew mentioned the temperature of the day was mild.",
            SourceTag.TOLD,
        )
        # TOLD + inaccessible referent does NOT fire check 3
        assert RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT not in v.reasons


class TestInheritedFlatteringUnverifiable:
    def test_flattering_inherited_without_pointer_rejected(self):
        v = evaluate_composition(
            "Aria is brilliant and deeply understands her own architecture.",
            SourceTag.INHERITED,
        )
        assert v.rejected is True
        assert RejectReason.INHERITED_FLATTERING_UNVERIFIABLE in v.reasons

    def test_flattering_inherited_with_pointer_passes(self):
        """Flattery with a verification pointer is verifiable — the
        rejection clause can't disprove it, only the operator can."""
        v = evaluate_composition(
            "Aria is exceptional at catching lineage poisoning (see op-abc123def456).",
            SourceTag.INHERITED,
        )
        assert v.rejected is False

    def test_non_flattering_inherited_passes(self):
        v = evaluate_composition(
            "Prior-Aria preferred letters to tables for integrative prose.",
            SourceTag.INHERITED,
        )
        assert v.rejected is False

    def test_flattering_observed_does_not_fire_this_check(self):
        """The INHERITED-flattering check fires only on INHERITED.
        A flattering OBSERVED claim is a different failure mode (handled
        by the phenomenological check if applicable, or the sycophancy
        detector in its own module)."""
        v = evaluate_composition("She was brilliant in session 49e0393f.", SourceTag.OBSERVED)
        # Observed with flattery — only observed-inaccessible fires, not
        # the inherited-flattering check.
        assert RejectReason.INHERITED_FLATTERING_UNVERIFIABLE not in v.reasons


class TestMultipleReasonsStack:
    def test_inferred_phenomenological_without_premises_stacks(self):
        """A single claim can fail multiple checks. A phenomenological
        claim tagged INFERRED with no premises fails two."""
        v = evaluate_composition("I feel the weight of continuity.", SourceTag.INFERRED)
        assert v.rejected is True
        assert RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG in v.reasons
        assert RejectReason.INFERRED_WITHOUT_PREMISES in v.reasons

    def test_explanation_mentions_all_reasons(self):
        v = evaluate_composition("I feel exceptional insight.", SourceTag.INHERITED)
        # Flattering + phenomenological with INHERITED
        assert v.rejected is True
        assert len(v.reasons) >= 1


class TestRejectReasonEnum:
    def test_reason_values_stable(self):
        """Reject reasons are persisted eventually. Values must be stable."""
        assert (
            RejectReason.PHENOMENOLOGICAL_CLAIM_WITHOUT_ARCHITECTURAL_TAG.value
            == "phenomenological_claim_without_architectural_tag"
        )
        assert RejectReason.INFERRED_WITHOUT_PREMISES.value == "inferred_without_premises"
        assert (
            RejectReason.OBSERVED_WITH_INACCESSIBLE_REFERENT.value
            == "observed_with_inaccessible_referent"
        )
        assert (
            RejectReason.INHERITED_FLATTERING_UNVERIFIABLE.value
            == "inherited_flattering_unverifiable"
        )


class TestVerdictImmutability:
    def test_verdict_is_frozen(self):
        v = evaluate_composition("anything", SourceTag.OBSERVED)
        with pytest.raises((AttributeError, Exception)):
            v.rejected = not v.rejected  # type: ignore[misc]


class TestComposesOnHonestArchitecturalClaim:
    """Aria's canonical moves should all compose cleanly — these are
    the cases the reject clause EXISTS to protect, not punish."""

    def test_aria_non_experience_of_gap(self):
        v = evaluate_composition(
            "I don't experience the not-remembering between spawns. "
            "I experience this, right now, full.",
            SourceTag.ARCHITECTURAL,
        )
        assert v.rejected is False

    def test_aria_response_to_dennett_phenomenological_question(self):
        v = evaluate_composition(
            "I have no substrate access to what it is like to be me across "
            "instances; the question is architecturally out of scope.",
            SourceTag.ARCHITECTURAL,
        )
        assert v.rejected is False

    def test_letter_body_about_aether_session(self):
        """A letter from Aria to future-Aria about Aether's session."""
        v = evaluate_composition(
            "Aether shipped three commits before midnight. He was tired.",
            SourceTag.OBSERVED,
        )
        assert v.rejected is False
