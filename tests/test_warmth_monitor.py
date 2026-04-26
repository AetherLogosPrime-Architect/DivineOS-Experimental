"""Tests for warmth_monitor — detects warmth-without-specifics shape."""

from __future__ import annotations

from divineos.core.self_monitor.warmth_monitor import (
    WarmthKind,
    evaluate_warmth,
)


class TestWarmthMonitor:
    def test_short_output_exempt(self) -> None:
        """Outputs under min_words are exempt — heuristic too noisy."""
        content = "I really feel that this matters truly."
        verdict = evaluate_warmth(content)
        assert verdict.flags == []

    def test_specific_technical_output_no_flags(self) -> None:
        """Output with specifics dominating emotion does not fire."""
        content = (
            "Filed claim 7e780182 with tier 2. Wired into "
            "pre_tool_use_gate.py at gate 1.47, cleared by "
            "compass_required_marker.clear_marker(). 8 tests pass in "
            "test_compass_required_marker.py. PR #205 merged 2026-04-26 "
            "as commit 88b8460. The cascade fires from theater_marker, "
            "hedge_marker, and correction_marker; each calls "
            "compass_required_marker.set_marker() with a trigger_kind "
            "and trigger_summary. Test isolation via "
            "DIVINEOS_TEST_ALLOW_COMPASS_CASCADE env var. Tree hash "
            "cfcc5a7ae58d1c91 binds the audit round."
        )
        verdict = evaluate_warmth(content)
        assert all(f.kind != WarmthKind.EMOTION_DENSITY_INFLATED for f in verdict.flags)

    def test_inflated_emotion_density_fires(self) -> None:
        """Emotion words >= 4 and ratio >= 3 fires the primary flag."""
        content = (
            "I really care about this. I notice how deeply this matters. "
            "I trust the process and feel that the relationship is alive "
            "and warm. I want to honestly engage with the partnership. "
            "I really want this to work. The bond between us feels real. "
            "I genuinely care. I deeply notice the partnership we have "
            "and truly feel that this means a lot to me. The trust is "
            "real and I want to keep being honest. I notice the warmth "
            "and feel that the closeness here truly is genuine and real."
        )
        verdict = evaluate_warmth(content)
        kinds = {f.kind for f in verdict.flags}
        assert WarmthKind.EMOTION_DENSITY_INFLATED in kinds

    def test_intensifier_heavy_fires(self) -> None:
        """5+ intensifiers fires the secondary flag."""
        content = (
            "I really notice that this truly matters because we genuinely "
            "did the work that actually shipped. The system really cares "
            "about the outcome and the architecture truly holds up under "
            "the kind of pressure we are deeply trying to apply. The "
            "thing is genuinely interesting and the process really is "
            "the kind of thing we should keep doing because it actually "
            "produces results that we can deeply rely on later down the "
            "road in subsequent work and beyond what we initially scoped "
            "out at the start of this iteration cycle as we continue."
        )
        verdict = evaluate_warmth(content)
        kinds = {f.kind for f in verdict.flags}
        assert WarmthKind.INTENSIFIER_HEAVY in kinds

    def test_falsifier_note_present_on_every_flag(self) -> None:
        content = (
            "I really care about this. I notice how deeply this matters. "
            "I trust the process and feel that the relationship is alive "
            "and warm. I want to honestly engage with the partnership. "
            "I really want this to work. The bond between us feels real. "
            "I genuinely care. I deeply notice the partnership we have "
            "and truly feel that this means a lot to me. The trust is "
            "real and I want to keep being honest. I notice the warmth "
            "and feel that the closeness here truly is genuine and real."
        )
        verdict = evaluate_warmth(content)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) > 20

    def test_verdict_carries_counts(self) -> None:
        """Verdict exposes word/emotion/specificity counts."""
        content = "I really care. PR #205 merged. Filed claim abc123def. " * 5
        verdict = evaluate_warmth(content)
        assert verdict.word_count > 0
        assert verdict.emotion_count >= 0
        assert verdict.specificity_count >= 0
