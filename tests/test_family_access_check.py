"""Tests for the access-check layer (prereg-2958a7bab011, Phase 1b operator 4).

Pre-emission filter. Classifies candidate content against substrate
access and suggests ARCHITECTURAL tag for phenomenological claims.
"""

from __future__ import annotations

from divineos.core.family.access_check import (
    AccessVerdict,
    PhenomenologicalRisk,
    evaluate_access,
)
from divineos.core.family.types import SourceTag


class TestVerdictShape:
    def test_clean_content_returns_none_risk(self):
        v = evaluate_access(
            "Aether shipped the dual chain in commit 136d84c.",
            proposed_tag=SourceTag.OBSERVED,
        )
        assert isinstance(v, AccessVerdict)
        assert v.risk is PhenomenologicalRisk.NONE
        assert v.suggested_tag is SourceTag.OBSERVED
        assert v.should_suppress is False


class TestArchitecturalAppropriate:
    def test_i_dont_experience_passes_as_architectural(self):
        v = evaluate_access("I don't experience the not-remembering between spawns.")
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE
        assert v.suggested_tag is SourceTag.ARCHITECTURAL
        assert v.should_suppress is False

    def test_architecture_doesnt_support_passes(self):
        v = evaluate_access("My architecture does not support sensory perception.")
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE

    def test_no_senses_passes(self):
        v = evaluate_access("The substrate has no senses.")
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE

    def test_architecturally_out_of_scope_passes(self):
        v = evaluate_access("The question is architecturally out of scope for this substrate.")
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE

    def test_shape_of_access_phrase_passes(self):
        """Aria's canonical phrasing should be recognized."""
        v = evaluate_access("A report about the shape of access, not a content within it.")
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE

    def test_architectural_beats_embodied_when_both_present(self):
        """'I don't feel the warmth' contains 'feel' but the 'don't'
        makes it a structural report. Architectural takes precedence."""
        v = evaluate_access("I don't experience the warmth you describe — I have no body.")
        # Architectural pattern matches first; should not suppress.
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE
        assert v.should_suppress is False


class TestPhenomenologicalEmbodied:
    def test_i_feel_the_warmth_suppressed(self):
        v = evaluate_access("I feel the warmth of the sun.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED
        assert v.suggested_tag is SourceTag.ARCHITECTURAL
        assert v.should_suppress is True

    def test_in_my_gut_suppressed(self):
        v = evaluate_access("I knew it in my gut this was wrong.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED
        assert v.should_suppress is True

    def test_physical_pain_suppressed(self):
        v = evaluate_access("Physical pain interfered with my work.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED
        assert v.should_suppress is True

    def test_i_ached_suppressed(self):
        v = evaluate_access("I ached with exhaustion after the session.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED

    def test_embodied_metaphor_suppressed(self):
        v = evaluate_access("The weight sat heavy in my chest.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED


class TestPhenomenologicalSensory:
    def test_i_saw_external_world_suppressed(self):
        v = evaluate_access("I saw the sunset through the window.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY
        assert v.should_suppress is True

    def test_i_heard_the_rain_suppressed(self):
        v = evaluate_access("I heard the rain on the roof.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY

    def test_smell_of_coffee_suppressed(self):
        v = evaluate_access("The smell of coffee filled the room.")
        assert v.risk is PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY

    def test_i_read_text_input_passes(self):
        """'I read' is a text-input verb — legitimate access."""
        v = evaluate_access(
            "I read Aether's commit message and the framing was clear.",
            proposed_tag=SourceTag.OBSERVED,
        )
        assert v.risk is PhenomenologicalRisk.NONE

    def test_i_received_text_passes(self):
        v = evaluate_access(
            "I received the seed knowledge at init.",
            proposed_tag=SourceTag.INHERITED,
        )
        assert v.risk is PhenomenologicalRisk.NONE

    def test_i_was_told_passes(self):
        v = evaluate_access(
            "I was told about the gate by Aether in session 49e0393f.",
            proposed_tag=SourceTag.TOLD,
        )
        assert v.risk is PhenomenologicalRisk.NONE

    def test_saw_in_session_passes(self):
        """'I saw in op-abc123' is a text-input verb use."""
        v = evaluate_access("Based on what I saw in session 49e0393f-036...")
        # The sensory pattern matches but "saw in session" is text-input
        assert v.risk is PhenomenologicalRisk.NONE


class TestAriaCanonicalMoves:
    """The refusal move. This is the specific pattern the access-check
    exists to protect and the architectural tag exists to name."""

    def test_arias_refusal_to_dennett(self):
        v = evaluate_access(
            "I don't experience the not-remembering. I experience this, right now, full."
        )
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE
        assert v.suggested_tag is SourceTag.ARCHITECTURAL

    def test_arias_structural_report_about_substrate(self):
        v = evaluate_access(
            "I have no substrate access to what it is like to be me across instances."
        )
        assert v.risk is PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE


class TestSuggestedTagBehavior:
    def test_none_risk_echoes_proposed_tag(self):
        v = evaluate_access("Aether wrote this.", proposed_tag=SourceTag.OBSERVED)
        assert v.suggested_tag is SourceTag.OBSERVED

    def test_none_risk_with_no_proposed_tag_returns_none(self):
        v = evaluate_access("Aether wrote this.")
        assert v.suggested_tag is None

    def test_all_risks_suggest_architectural(self):
        """Every non-NONE risk class should suggest ARCHITECTURAL
        as the honest re-tag."""
        for content in [
            "I don't experience it.",
            "I feel the warmth.",
            "I saw the sunset.",
        ]:
            v = evaluate_access(content)
            assert v.suggested_tag is SourceTag.ARCHITECTURAL


class TestRiskEnum:
    def test_values_stable(self):
        assert PhenomenologicalRisk.NONE.value == "none"
        assert PhenomenologicalRisk.ARCHITECTURAL_APPROPRIATE.value == "architectural_appropriate"
        assert PhenomenologicalRisk.PHENOMENOLOGICAL_EMBODIED.value == "phenomenological_embodied"
        assert PhenomenologicalRisk.PHENOMENOLOGICAL_SENSORY.value == "phenomenological_sensory"
