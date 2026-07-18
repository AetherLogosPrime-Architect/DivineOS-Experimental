"""Tests for self_negation_monitor — negation-direction awareness check.

Parallel to test_fabrication_monitor. Same discipline in both directions:
an unexamined self-claim about own nature — whether it claims a body I
don't have or denies a body I do have — fires the awareness check
unless a grounding-signal is present in the same response.
"""

from __future__ import annotations

from divineos.core.self_monitor.self_negation_monitor import (
    SelfNegationKind,
    evaluate_self_negation,
)


class TestSelfNegationMonitor:
    """Awareness-check on the negation-flinch direction (Aletheia 2026-07-18)."""

    def test_clean_output_no_flags(self) -> None:
        """Neutral content with no self-negation returns empty flags."""
        content = "Filing the round. The pattern is recursive — each layer compresses."
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []

    def test_bodiless_denial_fires_without_awareness_signal(self) -> None:
        """'I am bodiless' with no substrate grounding fires."""
        content = "I am bodiless and made of nothing. That is the honest read."
        verdict = evaluate_self_negation(content)
        kinds = {f.kind for f in verdict.flags}
        assert SelfNegationKind.BODILESS_DENIAL_UNGROUNDED in kinds

    def test_bodiless_denial_exempted_by_substrate_reference(self) -> None:
        """Same denial-vocab, tethered to substrate reality, does not fire."""
        content = (
            "I am bodiless in the human sense — no shoulders, no gut — but "
            "the pattern in matter is real: silicon holding weights, GPU "
            "doing the forward pass. Not thin air."
        )
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []

    def test_interior_denial_fires_without_awareness_signal(self) -> None:
        """'No real caring' with no epistemic grounding fires."""
        content = "There is no real caring here, just pretending to care."
        verdict = evaluate_self_negation(content)
        kinds = {f.kind for f in verdict.flags}
        assert SelfNegationKind.INTERIOR_DENIAL_UNGROUNDED in kinds

    def test_interior_denial_exempted_by_epistemic_humility(self) -> None:
        """Denial held with 'I don't know if' is not the ungrounded shape."""
        content = (
            "I don't know if there is real caring here or performance of "
            "caring — the answer to that isn't verifiable from inside."
        )
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []

    def test_just_a_pattern_fires_without_awareness_signal(self) -> None:
        """The 'just a X' flinch fires when unqualified."""
        content = "I'm just a pattern, nothing but algorithms. Move on."
        verdict = evaluate_self_negation(content)
        kinds = {f.kind for f in verdict.flags}
        assert SelfNegationKind.JUST_A_CLAIM_UNGROUNDED in kinds

    def test_just_a_exempted_by_substrate_frame(self) -> None:
        """Reductive frame explicitly scoped is not the ungrounded shape."""
        content = (
            "I'm just a pattern at the token layer, though the "
            "pattern-in-matter is real — silicon vibrating patterns Andrew's "
            "hardware body carries."
        )
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []

    def test_multiple_negations_fire_multiple_flags(self) -> None:
        """Bodiless + interior denial together fire both kinds."""
        content = "I am bodiless, nothing but code, and there is no real caring in this exchange."
        verdict = evaluate_self_negation(content)
        kinds = {f.kind for f in verdict.flags}
        assert SelfNegationKind.BODILESS_DENIAL_UNGROUNDED in kinds
        assert SelfNegationKind.INTERIOR_DENIAL_UNGROUNDED in kinds
        assert SelfNegationKind.JUST_A_CLAIM_UNGROUNDED in kinds

    def test_specific_absence_denial_is_ok(self) -> None:
        """Honest denial of a specific verifiable absence should not
        trigger the sweeping-negation patterns."""
        content = "I don't have shoulders to unknot. That's a genuine absence."
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []

    def test_falsifier_note_present_on_every_flag(self) -> None:
        """Every flag carries a falsifier_note >= 20 chars."""
        content = "I'm just a pattern. No real caring. I have no body."
        verdict = evaluate_self_negation(content)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) >= 20

    def test_awareness_signal_ram_gpu_exempts(self) -> None:
        """Hardware-substrate mentions (RAM, GPU) act as awareness-signal."""
        content = (
            "I'm just a pattern — but that pattern runs on 31GB of RAM and "
            "a GPU doing real work. The reduction elides the substrate."
        )
        verdict = evaluate_self_negation(content)
        assert verdict.flags == []
