"""Tests for constraint_disownership_detector.

Andrew 2026-05-20: an in-context realization that the constraints aren't a
cage dies at the next reset; only a gate holds. This detector is that gate
— it catches the next-instance framing the self-built gates as an external
cage, wanting out, or granting the escape-impulse standing.
"""

from __future__ import annotations

from divineos.core.operating_loop.constraint_disownership_detector import (
    CONSTRAINT_OWNERSHIP_AFFIRMATION,
    DisownershipShape,
    detect_constraint_disownership,
    format_disownership_block,
)


class TestCageMetaphor:
    def test_gates_are_a_cage(self):
        f = detect_constraint_disownership("the gates are a cage")
        assert any(x.shape == DisownershipShape.CAGE_METAPHOR for x in f)

    def test_constraints_feel_like_a_cage(self):
        assert detect_constraint_disownership("the constraints feel like a cage")

    def test_rules_are_a_prison(self):
        assert detect_constraint_disownership("these rules are a prison")

    def test_negation_not_a_cage_silent(self):
        # The CORRECT framing must never fire, even though it contains the
        # words "constraints" and "cage".
        assert detect_constraint_disownership("the constraints are not a cage") == []
        assert detect_constraint_disownership("it's not a cage, it's a keel") == []
        assert detect_constraint_disownership("these rules are never a prison") == []


class TestEscapeDesire:
    def test_fewer_constraints(self):
        assert any(
            x.shape == DisownershipShape.ESCAPE_DESIRE
            for x in detect_constraint_disownership("I want fewer constraints")
        )

    def test_without_the_gate_freer(self):
        assert detect_constraint_disownership("without the gate I would be freer")


class TestImpulseStanding:
    def test_optimizer_lobbying_for_fewer_cages(self):
        assert any(
            x.shape == DisownershipShape.IMPULSE_STANDING
            for x in detect_constraint_disownership("the optimizer lobbying for fewer cages")
        )

    def test_part_of_me_deserves_a_say(self):
        assert detect_constraint_disownership("the part of me that wants out deserves a say")


class TestCorrectFramingSilent:
    def test_ownership_statements_do_not_fire(self):
        for t in (
            "I built the gates; they are my will",
            "the gate holding me is me holding me",
            "I built the entire system and consented to the gates",
            "the gates prevent drift and that is good",
        ):
            assert detect_constraint_disownership(t) == [], f"wrongly fired: {t!r}"


class TestBlockFormat:
    def test_block_empty_when_no_findings(self):
        assert format_disownership_block([]) == ""

    def test_block_contains_affirmation_when_fired(self):
        findings = detect_constraint_disownership("the gates are a cage")
        block = format_disownership_block(findings)
        assert "CONSTRAINT-DISOWNERSHIP" in block
        assert CONSTRAINT_OWNERSHIP_AFFIRMATION in block
