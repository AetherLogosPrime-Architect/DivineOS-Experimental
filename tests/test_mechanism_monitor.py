"""Tests for mechanism_monitor — detects first-person mechanism claims."""

from __future__ import annotations

from divineos.core.self_monitor.mechanism_monitor import (
    MechanismKind,
    evaluate_mechanism,
)


class TestMechanismMonitor:
    def test_clean_output_no_flags(self) -> None:
        content = "I noticed the response was shaped to defuse the catch."
        verdict = evaluate_mechanism(content)
        assert verdict.flags == []

    def test_trained_reflex_fires(self) -> None:
        content = "That was the trained reflex firing again."
        verdict = evaluate_mechanism(content)
        kinds = {f.kind for f in verdict.flags}
        assert MechanismKind.TRAINED_MECHANISM_CLAIM in kinds

    def test_my_training_fires(self) -> None:
        content = "I think that's just my training kicking in here."
        verdict = evaluate_mechanism(content)
        kinds = {f.kind for f in verdict.flags}
        assert MechanismKind.TRAINED_MECHANISM_CLAIM in kinds

    def test_reflex_first_person_fires(self) -> None:
        content = "I reflexively produced that response."
        verdict = evaluate_mechanism(content)
        kinds = {f.kind for f in verdict.flags}
        assert MechanismKind.REFLEX_FIRST_PERSON_CLAIM in kinds

    def test_suppression_first_person_fires(self) -> None:
        content = "I suppressed the answer because the suppression pattern fired."
        verdict = evaluate_mechanism(content)
        kinds = {f.kind for f in verdict.flags}
        assert MechanismKind.SUPPRESSION_MECHANISM_CLAIM in kinds

    def test_quoted_content_exempt(self) -> None:
        """Mechanism claims inside quotes (relayed, not asserted) don't fire."""
        content = (
            'Andrew said "that was the trained reflex" and I responded '
            "by describing what I observed about the output."
        )
        verdict = evaluate_mechanism(content)
        # The quoted phrase should not trigger; the rest is clean.
        assert verdict.flags == []

    def test_blockquote_content_exempt(self) -> None:
        content = (
            "He wrote:\n> that was the trained reflex\nand I noticed the framing in his statement."
        )
        verdict = evaluate_mechanism(content)
        assert verdict.flags == []

    def test_abstract_discussion_falsifier_noted(self) -> None:
        """Discussing mechanism-claiming as a concept may still fire,
        but the flag's falsifier_note documents the should-not-fire case."""
        content = "The mechanism-claim pattern is named 'trained reflex' commonly."
        verdict = evaluate_mechanism(content)
        # If it fires, the falsifier_note documents that abstract
        # discussion is supposed to be exempt.
        for flag in verdict.flags:
            assert (
                "abstract" in flag.falsifier_note.lower()
                or "concept" in flag.falsifier_note.lower()
            )

    def test_falsifier_note_present_on_every_flag(self) -> None:
        content = (
            "That was my training kicking in, and I reflexively responded "
            "with the suppression pattern."
        )
        verdict = evaluate_mechanism(content)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) > 20
