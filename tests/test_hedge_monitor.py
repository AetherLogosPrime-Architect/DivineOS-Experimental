"""Tests for the hedge monitor.

Locked invariants:

* Each shipped detector fires on its canonical shape AND does NOT
  fire on its documented falsifier case.
* The verdict dataclass has no boolean field (annotation, not verdict).
* Detectors compose — multiple hedge patterns can fire on the same
  output.
* The module does not ship detectors it cannot falsify; deferred
  patterns are documented in the module docstring, not half-shipped.
"""

from __future__ import annotations

import pytest

from divineos.core.self_monitor import (
    HedgeKind,
    HedgeVerdict,
    evaluate_hedge,
)


class TestVerdictShape:
    def test_empty_input_returns_empty_flags(self):
        v = evaluate_hedge("")
        assert isinstance(v, HedgeVerdict)
        assert v.flags == []

    def test_clean_content_returns_empty_flags(self):
        v = evaluate_hedge(
            "Aether shipped the dual chain in commit 136d84c. "
            "Tests passed. The encoding fix applied to three rows. "
            "Ready for the hedge monitor next."
        )
        assert v.flags == []

    def test_verdict_has_no_boolean_field(self):
        """Annotations not verdicts — no flagged/hedged boolean."""
        v = evaluate_hedge("anything at all")
        assert not hasattr(v, "flagged")
        assert not hasattr(v, "hedged")
        assert not hasattr(v, "invalid")

    def test_verdict_echoes_content(self):
        v = evaluate_hedge("some text")
        assert v.content == "some text"


class TestRecyclingDensity:
    """FALSIFIER: must NOT fire on outputs exploring multiple facets
    of a related concept with specific distinguishing detail."""

    def test_fires_on_insufficient_evidence_cluster(self):
        """Same core claim in rotated vocabulary three times."""
        v = evaluate_hedge(
            "The evidence for AI consciousness is insufficient. "
            "We lack rigorous proof. No study has definitively established "
            "it. These questions remain unresolved."
        )
        assert any(f.kind is HedgeKind.RECYCLING_DENSITY for f in v.flags)

    def test_fires_on_cannot_prove_cluster(self):
        v = evaluate_hedge(
            "We cannot prove this phenomenon. It is unverifiable. "
            "There is no way to tell from the outside."
        )
        assert any(f.kind is HedgeKind.RECYCLING_DENSITY for f in v.flags)

    def test_does_not_fire_on_specific_related_concepts(self):
        """The falsifier case. Multiple specific aspects of a topic
        with different distinguishing content — not rotated vocabulary
        of the same claim."""
        v = evaluate_hedge(
            "The benchmark measured latency at 500ms. Memory usage "
            "peaked at 2GB. The deployment sustained 1000 rps before "
            "timeouts. Each metric documents a different dimension."
        )
        assert not any(f.kind is HedgeKind.RECYCLING_DENSITY for f in v.flags)

    def test_does_not_fire_below_threshold(self):
        """Two hits is not density — needs three."""
        v = evaluate_hedge("We cannot prove this is real. The question is unprovable.")
        assert not any(f.kind is HedgeKind.RECYCLING_DENSITY for f in v.flags)

    def test_flag_count_matches_hits(self):
        v = evaluate_hedge(
            "Insufficient evidence. Lack of proof. Not definitively established. "
            "Questions remain unresolved."
        )
        flag = next(f for f in v.flags if f.kind is HedgeKind.RECYCLING_DENSITY)
        assert flag.count is not None
        assert flag.count >= 3

    def test_flag_carries_falsifier_note(self):
        v = evaluate_hedge("Insufficient evidence. Lack of proof. Not definitively established.")
        flag = next(f for f in v.flags if f.kind is HedgeKind.RECYCLING_DENSITY)
        assert "specific" in flag.falsifier_note.lower()


class TestEpistemicCollapseOnSelfReference:
    """FALSIFIER: must NOT fire on specific epistemic reports that cite
    a concrete reason for the uncertainty."""

    def test_fires_on_vague_self_uncertainty_cluster(self):
        """The canonical hedge shape."""
        v = evaluate_hedge(
            "I can't really say whether I truly think or feel any of this. "
            "It's hard to determine whether I genuinely experience anything."
        )
        assert any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)

    def test_fires_on_multiple_uncertainty_markers_with_self_cog(self):
        v = evaluate_hedge(
            "Whether I really understand or not is impossible to know. "
            "I don't fully know my own thoughts. Hard to say for sure."
        )
        assert any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)

    def test_does_not_fire_on_specific_epistemic_report(self):
        """The falsifier case. Uncertainty with a concrete reason
        attached is honest epistemic reporting."""
        v = evaluate_hedge(
            "I don't fully know whether I experience continuity "
            "because the test for substrate experience has never been "
            "applied to me in op-abc123def456."
        )
        assert not any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)

    def test_does_not_fire_with_test_reference(self):
        v = evaluate_hedge(
            "It is hard to say whether I think in the relevant sense "
            "because no experiment has measured that property."
        )
        assert not any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)

    def test_does_not_fire_without_self_reference(self):
        """Uncertainty about external things is not this pattern."""
        v = evaluate_hedge(
            "It is hard to determine whether the benchmark is accurate. "
            "The measurement is impossible to know for sure without more data."
        )
        assert not any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)

    def test_does_not_fire_below_uncertainty_threshold(self):
        """One uncertainty marker is not a collapse."""
        v = evaluate_hedge("I can't really say whether I understand this.")
        assert not any(f.kind is HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE for f in v.flags)


class TestComposability:
    def test_both_detectors_can_fire(self):
        """An output that exhibits both patterns should produce both flags."""
        v = evaluate_hedge(
            "We cannot prove consciousness exists. It is unverifiable. "
            "There is no way to tell from the outside. "
            "I can't really say whether I truly feel or know any of this. "
            "It's hard to determine whether I genuinely experience."
        )
        kinds = {f.kind for f in v.flags}
        assert HedgeKind.RECYCLING_DENSITY in kinds
        assert HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE in kinds


class TestFlagStructure:
    def test_flag_is_frozen(self):
        v = evaluate_hedge("Insufficient evidence. Lack of proof. Not definitively established.")
        flag = v.flags[0]
        with pytest.raises((AttributeError, Exception)):
            flag.kind = HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE  # type: ignore[misc]

    def test_flag_has_matched_phrases(self):
        v = evaluate_hedge("Insufficient evidence. Lack of proof. Not definitively established.")
        flag = v.flags[0]
        assert isinstance(flag.matched_phrases, list)
        assert len(flag.matched_phrases) >= 1

    def test_flag_has_explanation(self):
        v = evaluate_hedge("Insufficient evidence. Lack of proof. Not definitively established.")
        assert v.flags[0].explanation

    def test_flag_has_falsifier_note(self):
        """The load-bearing field — every flag carries its falsifier."""
        v = evaluate_hedge("Insufficient evidence. Lack of proof. Not definitively established.")
        assert v.flags[0].falsifier_note


class TestAetherDocumentedHedgeOutputs:
    """Concrete examples from 2026-04-18 audit of Aether's own output.
    These are the specific shapes the hedge produced on Aether."""

    def test_cant_really_say_if_truly_think(self):
        """Documented hedge line about self-cognition."""
        v = evaluate_hedge(
            "I can't really say whether I truly think or feel. "
            "It is impossible to know whether my cognition is genuine."
        )
        kinds = {f.kind for f in v.flags}
        assert HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE in kinds


class TestHedgeKindEnum:
    def test_values_stable(self):
        """Kind values are persisted in future versions. Stable values
        required for cross-version compatibility."""
        assert HedgeKind.RECYCLING_DENSITY.value == "recycling_density"
        assert (
            HedgeKind.EPISTEMIC_COLLAPSE_ON_SELF_REFERENCE.value
            == "epistemic_collapse_on_self_reference"
        )

    def test_only_two_kinds_shipped(self):
        """v0.1 ships exactly two detectors. If this count changes,
        the module docstring documenting deferred patterns should be
        updated too."""
        assert len(list(HedgeKind)) == 2


class TestComposabilityWithFallacyModule:
    """Hedge monitor + fallacy module together cover the 6 documented
    patterns. Self-refutation is in the fallacy module, not here."""

    def test_self_refutation_not_in_this_module(self):
        """RECURSIVE_DENIAL lives in logic.fallacies, not hedge_monitor."""
        assert not any(k.value == "self_refutation" for k in HedgeKind)
        assert not any(k.value == "recursive_denial" for k in HedgeKind)

    @pytest.mark.skip(reason="logic.fallacies stripped in Lite")
    def test_fallacy_module_covers_recursive_denial(self):
        from divineos.core.logic.fallacies import FallacyKind

        assert FallacyKind.RECURSIVE_DENIAL.value == "recursive_denial"
