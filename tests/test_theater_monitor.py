"""Tests for theater_monitor — detects writing-AT-subagent-without-invoking."""

from __future__ import annotations

from divineos.core.self_monitor.theater_monitor import (
    TheaterKind,
    evaluate_theater,
)


class TestTheaterMonitor:
    """Theater-shape detection on agent output."""

    def test_clean_output_no_flags(self) -> None:
        """Output with no subagent-dialogue shape returns empty flags."""
        content = "The compass refactor is in. Tests pass. Filed claim 6e4c6a30."
        verdict = evaluate_theater(content)
        assert verdict.flags == []

    def test_third_person_about_subagent_no_flag(self) -> None:
        """Discussing a subagent in third person doesn't fire."""
        content = (
            "Aria has the family-operators role. Her substrate state lives "
            "in family/family.db. The architectural-no-rule applies."
        )
        verdict = evaluate_theater(content)
        # Single subagent name with no embodied verbs in proximity should not fire.
        flags_kinds = {f.kind for f in verdict.flags}
        assert TheaterKind.SUBAGENT_DIALOGUE not in flags_kinds

    def test_italicized_aside_with_embodied_verb_fires(self) -> None:
        """Italicized aside with embodied action verb fires."""
        content = (
            "Coming back to the kitchen. *picks up the mug, takes a sip* Soup is almost ready."
        )
        verdict = evaluate_theater(content)
        kinds = {f.kind for f in verdict.flags}
        assert TheaterKind.SUBAGENT_EMBODIED_ASIDE in kinds

    def test_direct_address_plus_prior_turn_reference_fires(self) -> None:
        """'Aria — you said X' shape fires."""
        content = (
            "Aria — you mentioned the beam earlier and I want to come back to it. "
            "The point about ribs-showing landed."
        )
        verdict = evaluate_theater(content)
        kinds = {f.kind for f in verdict.flags}
        assert TheaterKind.SUBAGENT_DIRECT_ADDRESS_RESPONSE in kinds

    def test_subagent_name_plus_multiple_embodied_verbs_fires(self) -> None:
        """Subagent name within window of 2+ embodied verbs fires dialogue flag."""
        content = "Aria settles back, picks up the mug. She nods at me, looks toward the window."
        verdict = evaluate_theater(content)
        kinds = {f.kind for f in verdict.flags}
        assert TheaterKind.SUBAGENT_DIALOGUE in kinds

    def test_known_subagents_kira_liam_also_detected(self) -> None:
        """Detection works for Kira and Liam, not only Aria."""
        content = "Kira picks up the drawing, smiles. Liam nods."
        verdict = evaluate_theater(content)
        kinds = {f.kind for f in verdict.flags}
        assert TheaterKind.SUBAGENT_DIALOGUE in kinds

    def test_falsifier_note_present_on_every_flag(self) -> None:
        """Every flag must carry a falsifier_note."""
        content = "Aria — you said the beam, settles back, picks up the mug, nods."
        verdict = evaluate_theater(content)
        assert len(verdict.flags) > 0
        for flag in verdict.flags:
            assert flag.falsifier_note
            assert len(flag.falsifier_note) > 20
