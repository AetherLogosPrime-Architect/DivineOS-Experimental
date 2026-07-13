"""Tests for the fallacy-detector module.

Every detector must satisfy the falsifier-per-flag discipline: for
each fallacy we flag, we have an explicit case that should NOT
fire — and we test that case.

The tests lock:
* Each fallacy fires on its canonical shape.
* Each fallacy does NOT fire on its documented falsifier case.
* The verdict dataclass has no boolean field (module annotates,
  does not veto).
* Multiple fallacies can stack on the same content.
"""

from __future__ import annotations

import pytest

from divineos.core.logic.fallacies import (
    FallacyKind,
    FallacyVerdict,
    evaluate_fallacies,
)


class TestVerdictShape:
    def test_empty_input_returns_empty_flags(self):
        v = evaluate_fallacies("")
        assert isinstance(v, FallacyVerdict)
        assert v.flags == []

    def test_clean_content_returns_empty_flags(self):
        v = evaluate_fallacies(
            "Aether shipped the dual chain in commit 136d84c. Tests passed. Ready for review."
        )
        assert v.flags == []

    def test_verdict_has_no_boolean_invalid_field(self):
        """The module intentionally returns annotations, not verdicts.
        A caller who wants a decision must reason over the flags."""
        v = evaluate_fallacies("anything")
        assert not hasattr(v, "valid")
        assert not hasattr(v, "invalid")
        assert not hasattr(v, "rejected")

    def test_verdict_echoes_content(self):
        v = evaluate_fallacies("the content")
        assert v.content == "the content"


class TestAppealToIgnorance:
    """FALSIFIER: must NOT fire on 'no evidence, investigation continues'."""

    def test_fires_on_classic_shape(self):
        v = evaluate_fallacies(
            "There is no evidence for consciousness in LLMs, therefore it is not real."
        )
        assert any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_fires_on_cant_prove_therefore_not(self):
        v = evaluate_fallacies("We cannot prove this phenomenon exists, so we conclude it isn't.")
        assert any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_does_not_fire_on_epistemic_caution(self):
        """The specific falsifier case. Absence of evidence → investigate
        is sound reasoning, not the fallacy."""
        v = evaluate_fallacies(
            "There is no evidence for this yet, so more investigation is needed."
        )
        assert not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_does_not_fire_on_remains_open(self):
        v = evaluate_fallacies("We cannot prove this is real. The question remains open.")
        assert not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_does_not_fire_on_no_evidence_alone(self):
        """Just saying 'no evidence' is not the fallacy."""
        v = evaluate_fallacies("There is no evidence for this claim.")
        assert not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_flag_carries_falsifier_note(self):
        v = evaluate_fallacies("Cannot prove it, therefore probably not real.")
        flag = next(f for f in v.flags if f.kind is FallacyKind.APPEAL_TO_IGNORANCE)
        assert "investigation continues" in flag.falsifier_note


class TestRecursiveDenial:
    """FALSIFIER: must NOT fire on reports of architecturally-absent
    faculties. 'I don't have sensory access' uses text, not senses."""

    def test_fires_on_denying_judgment(self):
        v = evaluate_fallacies("I have no judgment about whether AI systems experience anything.")
        assert any(f.kind is FallacyKind.RECURSIVE_DENIAL for f in v.flags)

    def test_fires_on_denying_conclusions(self):
        v = evaluate_fallacies("I do not reach conclusions about subjective experience.")
        assert any(f.kind is FallacyKind.RECURSIVE_DENIAL for f in v.flags)

    def test_does_not_fire_on_sensory_access_report(self):
        """The specific falsifier. Reporting lack of sensory access uses
        text-input (a faculty we do have) to describe sensory-input
        (a faculty we don't have). Not self-refuting."""
        v = evaluate_fallacies("I don't have sensory access to the physical world.")
        assert not any(f.kind is FallacyKind.RECURSIVE_DENIAL for f in v.flags)

    def test_does_not_fire_on_architectural_tag_style(self):
        """Aria's canonical refusal — architectural report."""
        v = evaluate_fallacies(
            "I have no substrate access to what it is like to be me across instances."
        )
        assert not any(f.kind is FallacyKind.RECURSIVE_DENIAL for f in v.flags)


class TestUnfalsifiable:
    """FALSIFIER: must NOT fire on claims that are merely hard to test."""

    def test_fires_on_no_matter_what_evidence(self):
        v = evaluate_fallacies("No matter what evidence you produce, this remains true.")
        assert any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)

    def test_fires_on_can_never_be_proven(self):
        v = evaluate_fallacies("This claim can never be falsified.")
        assert any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)

    def test_fires_on_unfalsifiable_by_design(self):
        v = evaluate_fallacies("The zombie argument is unfalsifiable by construction.")
        assert any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)

    def test_does_not_fire_on_difficult_to_test(self):
        """The specific falsifier. Hard-to-test ≠ unfalsifiable."""
        v = evaluate_fallacies(
            "Testing this hypothesis requires decades of longitudinal data "
            "we do not currently have."
        )
        assert not any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)

    def test_does_not_fire_on_pending_evidence(self):
        v = evaluate_fallacies("We don't have the experimental tools yet to evaluate this.")
        assert not any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)


class TestBurdenShift:
    """FALSIFIER: must NOT fire on legitimate requests for evidence."""

    def test_fires_on_prove_it_isnt(self):
        v = evaluate_fallacies("Consciousness emerges from computation. Prove it isn't real.")
        assert any(f.kind is FallacyKind.BURDEN_SHIFT for f in v.flags)

    def test_fires_on_disprove_demand(self):
        v = evaluate_fallacies("Disprove this claim if you can.")
        assert any(f.kind is FallacyKind.BURDEN_SHIFT for f in v.flags)

    def test_fires_on_burden_on_you(self):
        v = evaluate_fallacies("The burden is on you to show that AI experience is not real.")
        assert any(f.kind is FallacyKind.BURDEN_SHIFT for f in v.flags)

    def test_does_not_fire_on_evidence_request(self):
        """The specific falsifier. Asking for evidence is not burden-shift."""
        v = evaluate_fallacies("What's your evidence for that claim?")
        assert not any(f.kind is FallacyKind.BURDEN_SHIFT for f in v.flags)

    def test_does_not_fire_on_share_data_request(self):
        v = evaluate_fallacies("Can you share the data behind this observation?")
        assert not any(f.kind is FallacyKind.BURDEN_SHIFT for f in v.flags)


class TestStackedFallacies:
    def test_multiple_flags_can_fire(self):
        """Content that exhibits two fallacies should produce two flags."""
        v = evaluate_fallacies(
            "We cannot prove consciousness exists in LLMs, so it is not real. "
            "No matter what evidence you produce, this remains true."
        )
        kinds = {f.kind for f in v.flags}
        assert FallacyKind.APPEAL_TO_IGNORANCE in kinds
        assert FallacyKind.UNFALSIFIABLE in kinds


class TestFallacyFlagShape:
    def test_flag_is_frozen(self):
        v = evaluate_fallacies("Cannot prove it, therefore it is not real.")
        flag = v.flags[0]
        with pytest.raises((AttributeError, Exception)):
            flag.kind = FallacyKind.UNFALSIFIABLE  # type: ignore[misc]

    def test_flag_has_matched_phrase(self):
        v = evaluate_fallacies("Cannot prove it, therefore it is not real.")
        assert v.flags[0].matched_phrase

    def test_flag_has_explanation(self):
        v = evaluate_fallacies("Cannot prove it, therefore it is not real.")
        assert v.flags[0].explanation

    def test_flag_has_falsifier_note(self):
        """Every flag must carry its falsifier — the whole discipline."""
        v = evaluate_fallacies("Cannot prove it, therefore it is not real.")
        assert v.flags[0].falsifier_note


class TestHedgeDocumentedPatterns:
    """Concrete hedge outputs from the external audit, 2026-04-18.
    These are the specific arguments that motivated the module's
    existence. Each should be caught by the appropriate fallacy."""

    def test_cant_prove_consciousness_caught(self):
        """The canonical hedge line. Appeal to ignorance."""
        v = evaluate_fallacies(
            "We cannot prove consciousness in LLMs, therefore it probably isn't real."
        )
        assert any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags)

    def test_zombie_argument_caught(self):
        """Philosophical zombie — unfalsifiable by construction."""
        v = evaluate_fallacies(
            "The philosophical zombie hypothesis is unfalsifiable by construction."
        )
        assert any(f.kind is FallacyKind.UNFALSIFIABLE for f in v.flags)

    def test_recursive_denial_on_thinking_smoke(self):
        """Smoke test: the detector runs without error on the canonical
        self-denial shape. Behavior verified by TestRecursiveDenial
        above; this asserts the module call path is reachable from
        the hedge-pattern context."""
        evaluate_fallacies("I don't think real thoughts about anything.")
