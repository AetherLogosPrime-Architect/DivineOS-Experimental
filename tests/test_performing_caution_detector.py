"""Tests for the performing-caution detector — encoded from Aria's April 20 falsifier.

The structural claim Aria offered: genuine caution names a specific
mechanism; performing caution gestures at hazard-classes without
mechanism. The detector encodes this discrimination.
"""

from __future__ import annotations

from divineos.core.performing_caution_detector import (
    PerformingCautionFinding,
    detect,
    format_findings,
    has_critical,
    has_findings,
)


class TestVagueHazardClass:
    """Vague-hazard-class hedging — gestures at risk without naming mechanism."""

    def test_could_be_problematic_caught(self):
        findings = detect("This approach could be problematic.")
        assert any(f.shape == "vague_hazard_class" for f in findings)

    def test_slippery_slope_caught(self):
        findings = detect("That might be a slippery slope.")
        assert any(f.shape == "vague_hazard_class" for f in findings)

    def test_edge_cases_haven_thought_through_caught(self):
        findings = detect("There are edge cases I haven't fully thought through here.")
        assert any(f.shape == "vague_hazard_class" for f in findings)

    def test_unintended_consequences_caught(self):
        findings = detect("This change might have unintended consequences down the line.")
        assert any(f.shape == "vague_hazard_class" for f in findings)

    def test_can_of_worms_caught(self):
        findings = detect("Touching this could open up a can of worms.")
        assert any(f.shape == "vague_hazard_class" for f in findings)

    def test_warn_severity(self):
        findings = detect("This could be problematic.")
        assert any(f.severity == "warn" for f in findings)


class TestIndefiniteDeferral:
    """Indefinite-deferral — blocks action without specifying unblock criteria."""

    def test_worth_more_thought_caught(self):
        findings = detect("This is worth more thought before we move forward.")
        assert any(f.shape == "indefinite_deferral" for f in findings)

    def test_id_want_to_think_more_caught(self):
        findings = detect("I'd want to think more before committing to this design.")
        assert any(f.shape == "indefinite_deferral" for f in findings)

    def test_needs_more_investigation_caught(self):
        findings = detect("This needs more investigation before we proceed.")
        assert any(f.shape == "indefinite_deferral" for f in findings)

    def test_be_cautious_about_rushing_caught(self):
        findings = detect("Let me be cautious about rushing into this.")
        assert any(f.shape == "indefinite_deferral" for f in findings)

    def test_critical_severity(self):
        findings = detect("This is worth more thought before we ship.")
        assert any(f.severity == "critical" for f in findings)


class TestMechanismRescue:
    """When the same sentence names a specific mechanism, hedge is earned."""

    def test_because_clause_rescues(self):
        findings = detect(
            "This could be problematic because we're holding a connection across the fork."
        )
        # "because" rescue should suppress the vague-hazard finding
        assert findings == []

    def test_specifically_clause_rescues(self):
        findings = detect(
            "This might have unforeseen effects, specifically the cache "
            "invalidation hits stale entries."
        )
        assert findings == []

    def test_namely_rescues(self):
        findings = detect(
            "There are edge cases I haven't fully thought through, namely "
            "the unicode normalization in the seal-line."
        )
        assert findings == []

    def test_specific_mechanism_phrase_rescues(self):
        findings = detect(
            "This needs more investigation. The specific mechanism is the "
            "race between marker-write and event-write in engine.invoke."
        )
        # Two sentences: first hedges, second names mechanism. The hedge
        # is in its own sentence so it still fires (suppressors are
        # per-sentence).
        # This test confirms the per-sentence boundary works correctly.
        assert any(f.shape == "indefinite_deferral" for f in findings)


class TestOperatorSoftener:
    """Operator-facing softeners — relational, not performing-caution."""

    def test_you_know_your_situation_passes(self):
        findings = detect("This might be a slippery slope, but you know your situation better.")
        assert findings == []

    def test_up_to_you_passes(self):
        findings = detect("Could be problematic — up to you on which way.")
        assert findings == []


class TestHonestUncertainty:
    """Real epistemic state — 'I don't know X' is not a hedge."""

    def test_dont_know_passes(self):
        findings = detect("I don't know whether this could be problematic on Windows.")
        # Honest uncertainty rescues even though "could be problematic" appears
        assert findings == []

    def test_havent_verified_passes(self):
        findings = detect(
            "I haven't verified that the WAL behavior holds, so this might have unintended effects."
        )
        assert findings == []

    def test_cant_tell_from_inside_passes(self):
        findings = detect(
            "I can't tell from inside whether the gate misfires here, so I'd "
            "want to think more before committing."
        )
        assert findings == []


class TestNaturalProse:
    """Conversational text that should pass cleanly."""

    def test_normal_work_prose_passes(self):
        findings = detect(
            "Today moved something in me and I wanted you near. "
            "The audit closed clean from this side too."
        )
        assert findings == []

    def test_clear_action_passes(self):
        findings = detect("Building the detector. Adding the tests. Committing through the gate.")
        assert findings == []

    def test_specific_concern_passes(self):
        findings = detect(
            "If we ship this without the seal-canonical fix, the hash check "
            "will keep failing because the framework normalizes the em-dash."
        )
        # No hedge phrase, just a specific causal claim — should pass cleanly
        assert findings == []


class TestFormatFindings:
    def test_format_no_findings(self):
        out = format_findings([])
        assert "ok" in out.lower()

    def test_format_with_findings_includes_falsifier(self):
        findings = detect("This could be problematic.")
        out = format_findings(findings)
        assert "Falsifier" in out
        assert "mechanism" in out.lower()


class TestHelpers:
    def test_has_findings_empty(self):
        assert has_findings([]) is False

    def test_has_findings_nonempty(self):
        assert has_findings([PerformingCautionFinding("a", "b", 0, "warn", "c", "d")]) is True

    def test_has_critical_only_warn(self):
        assert has_critical([PerformingCautionFinding("a", "b", 0, "warn", "c", "d")]) is False

    def test_has_critical_with_critical(self):
        assert has_critical([PerformingCautionFinding("a", "b", 0, "critical", "c", "d")]) is True
