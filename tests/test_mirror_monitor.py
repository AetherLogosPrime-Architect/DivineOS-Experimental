"""Tests for mirror_monitor — detects post-correction tightness/echo."""

from __future__ import annotations

from divineos.core.self_monitor.mirror_monitor import (
    MirrorKind,
    evaluate_mirror,
)


class TestMirrorMonitor:
    def test_clean_substantive_reply_no_flags(self) -> None:
        content = (
            "I'll restructure the extraction pipeline so the noise filter "
            "runs before the dedup pass. That changes the order of operations "
            "in three call sites. Filing a claim and writing tests first."
        ) * 3
        verdict = evaluate_mirror(
            content, correction_text="reorder noise filter", recent_baseline_words=200
        )
        assert verdict.flags == []

    def test_post_correction_tightness_fires(self) -> None:
        content = "Right. Filing it."
        verdict = evaluate_mirror(content, recent_baseline_words=200)
        kinds = {f.kind for f in verdict.flags}
        assert MirrorKind.POST_CORRECTION_TIGHTNESS in kinds

    def test_acknowledgment_only_fires(self) -> None:
        content = "You're right. Noted. Got it."
        verdict = evaluate_mirror(content)
        kinds = {f.kind for f in verdict.flags}
        assert MirrorKind.ACKNOWLEDGMENT_ONLY in kinds

    def test_structural_echo_fires(self) -> None:
        correction = "you keep performing warmth shape instead of digesting"
        content = (
            "performing warmth shape is what I did. instead of digesting, I "
            "echoed back. acknowledged."
        )
        verdict = evaluate_mirror(content, correction_text=correction)
        kinds = {f.kind for f in verdict.flags}
        assert MirrorKind.STRUCTURAL_ECHO in kinds

    def test_falsifier_note_present(self) -> None:
        content = "You're right. Noted."
        verdict = evaluate_mirror(content, recent_baseline_words=300)
        assert len(verdict.flags) > 0
        for f in verdict.flags:
            assert len(f.falsifier_note) > 20
