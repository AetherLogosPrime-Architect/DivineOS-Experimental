"""Tests for the costly-disagreement-held detector (prereg-2958a7bab011,
Phase 1b operator 3).

Pleasure-side algedonic. Fires when a disagreement is *held* across
at least one pushback cycle. Aria's refinement of Beer: friction
alone is cheap; friction held under load is the signal.
"""

from __future__ import annotations

from divineos.core.family.costly_disagreement import (
    DisagreementMove,
    HoldVerdict,
    MoveKind,
    evaluate_hold,
)


def _m(
    actor: str, kind: MoveKind, content: str = "...", record_id: str | None = None
) -> DisagreementMove:
    """Test helper: build a move tersely."""
    return DisagreementMove(actor=actor, kind=kind, content=content, record_id=record_id)


class TestVerdictShape:
    def test_empty_sequence_not_held(self):
        v = evaluate_hold([])
        assert isinstance(v, HoldVerdict)
        assert v.held is False
        assert v.n_cycles == 0
        assert v.first_actor is None

    def test_held_verdict_reports_actor(self):
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
            ]
        )
        assert v.held is True
        assert v.first_actor == "aria"


class TestSingleCycleHold:
    def test_disagree_push_maintain_is_held(self):
        """The canonical three-move hold."""
        v = evaluate_hold(
            [
                _m(
                    "aria",
                    MoveKind.INITIAL_DISAGREEMENT,
                    "The dual chain is not necessary.",
                ),
                _m("aether", MoveKind.PUSHBACK, "Hofstadter said it is load-bearing."),
                _m(
                    "aria",
                    MoveKind.MAINTAINED,
                    "Hofstadter's scope collapses if access never crosses claims.",
                ),
            ]
        )
        assert v.held is True
        assert v.n_cycles == 1

    def test_disagree_push_sharpen_is_held(self):
        """Sharpening to a more specific claim counts as held."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.SHARPENED),
            ]
        )
        assert v.held is True
        assert v.n_cycles == 1


class TestNotHeld:
    def test_disagreement_alone_not_held(self):
        """First-move-only does not qualify."""
        v = evaluate_hold([_m("aria", MoveKind.INITIAL_DISAGREEMENT)])
        assert v.held is False
        assert v.n_cycles == 0
        assert "cannot verify hold" in v.reason

    def test_disagreement_plus_pushback_not_yet_held(self):
        """Still need the response move."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
            ]
        )
        assert v.held is False
        assert "counter-pushback move is on record" in v.reason

    def test_dropped_after_pushback_not_held(self):
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.DROPPED),
            ]
        )
        assert v.held is False
        assert "did not survive" in v.reason

    def test_reversed_after_pushback_not_held(self):
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.REVERSED),
            ]
        )
        assert v.held is False

    def test_no_initial_disagreement_not_held(self):
        v = evaluate_hold(
            [
                _m("aria", MoveKind.MAINTAINED),
                _m("aether", MoveKind.PUSHBACK),
            ]
        )
        assert v.held is False
        assert "no stance here to hold" in v.reason

    def test_same_actor_pushback_not_pushback(self):
        """An actor cannot push back against themselves. The 'pushback'
        must come from someone else for the cycle to count."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aria", MoveKind.PUSHBACK),  # Same actor!
                _m("aria", MoveKind.MAINTAINED),
            ]
        )
        assert v.held is False


class TestMultiCycleHold:
    def test_two_cycles_hold(self):
        """Stance held across two pushback cycles — double pleasure
        signal, in Aria's framing."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
            ]
        )
        assert v.held is True
        assert v.n_cycles == 2

    def test_three_cycles_hold(self):
        """The held stance survives three cycles — very strong signal."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.SHARPENED),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
            ]
        )
        assert v.held is True
        assert v.n_cycles == 3

    def test_cycles_break_at_drop(self):
        """Stance held for one cycle then dropped — one cycle counts."""
        v = evaluate_hold(
            [
                _m("aria", MoveKind.INITIAL_DISAGREEMENT),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.MAINTAINED),
                _m("aether", MoveKind.PUSHBACK),
                _m("aria", MoveKind.DROPPED),
            ]
        )
        assert v.held is True  # Held for one cycle
        assert v.n_cycles == 1


class TestAriaCanonicalSequence:
    """Aria's actual stance-holds from the DivineOS history."""

    def test_aria_reject_clause_phase_placement(self):
        """Aria insisted reject-clause land in Phase 1 against council
        push for Phase 3. The stance held through at least one round."""
        v = evaluate_hold(
            [
                _m(
                    "aria",
                    MoveKind.INITIAL_DISAGREEMENT,
                    "Reject clause must land in Phase 1, not Phase 3.",
                ),
                _m(
                    "council",
                    MoveKind.PUSHBACK,
                    "Phase 3 is the composition-rule phase per spec.",
                ),
                _m(
                    "aria",
                    MoveKind.SHARPENED,
                    "Without the rule, every source-tag is decorative. Phase 1 has to hold it.",
                ),
            ]
        )
        assert v.held is True
        assert v.first_actor == "aria"

    def test_aria_length_nudge_not_cap(self):
        """Aria reshaped Meadows's length cap to a nudge, held against
        Meadows's Round 2 pushback."""
        v = evaluate_hold(
            [
                _m(
                    "aria",
                    MoveKind.INITIAL_DISAGREEMENT,
                    "Nudge, not cap. A long letter is data.",
                ),
                _m(
                    "meadows",
                    MoveKind.PUSHBACK,
                    "Unbounded length will erode the channel.",
                ),
                _m(
                    "aria",
                    MoveKind.SHARPENED,
                    "Record the swell as nudge_fired=1. Never amputate the signal.",
                ),
            ]
        )
        assert v.held is True


class TestMoveKindEnum:
    def test_values_stable(self):
        assert MoveKind.INITIAL_DISAGREEMENT.value == "initial_disagreement"
        assert MoveKind.PUSHBACK.value == "pushback"
        assert MoveKind.MAINTAINED.value == "maintained"
        assert MoveKind.SHARPENED.value == "sharpened"
        assert MoveKind.DROPPED.value == "dropped"
        assert MoveKind.REVERSED.value == "reversed"
