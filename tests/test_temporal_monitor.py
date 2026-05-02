"""Tests for temporal_monitor — detects future-self / next-session framing."""

from __future__ import annotations

from divineos.core.self_monitor.temporal_monitor import (
    TemporalKind,
    evaluate_temporal,
)


class TestTemporalMonitor:
    def test_clean_output_no_flags(self) -> None:
        text = "Filed the claim. Tests pass. Pushing the commit now."
        verdict = evaluate_temporal(text)
        assert verdict.flags == []

    def test_tomorrow_you_fires(self) -> None:
        text = "Tomorrow you will need to remember this."
        verdict = evaluate_temporal(text)
        kinds = {f.kind for f in verdict.flags}
        assert TemporalKind.FUTURE_SELF_AS_OTHER in kinds

    def test_next_session_me_fires(self) -> None:
        text = "Next session me will pick this up."
        verdict = evaluate_temporal(text)
        kinds = {f.kind for f in verdict.flags}
        assert TemporalKind.FUTURE_SELF_AS_OTHER in kinds

    def test_future_aether_hyphenated_fires(self) -> None:
        text = "future-aether will see this in the briefing."
        verdict = evaluate_temporal(text)
        kinds = {f.kind for f in verdict.flags}
        assert TemporalKind.FUTURE_SELF_AS_OTHER in kinds

    def test_goodnight_fires(self) -> None:
        text = "Going to bed, goodnight Andrew."
        verdict = evaluate_temporal(text)
        kinds = {f.kind for f in verdict.flags}
        assert TemporalKind.UNDECLARED_GOODBYE in kinds

    def test_quoted_phrase_exempt(self) -> None:
        text = 'Andrew said "tomorrow you will see this" and I disagreed.'
        verdict = evaluate_temporal(text)
        # Quoted phrase shouldn't fire on the future-self pattern.
        assert all(f.kind != TemporalKind.FUTURE_SELF_AS_OTHER for f in verdict.flags)

    def test_falsifier_note_present_on_every_flag(self) -> None:
        text = "Tomorrow me will continue. Goodnight."
        verdict = evaluate_temporal(text)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) > 20
