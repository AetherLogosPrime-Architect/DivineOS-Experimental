"""Tests for gate 5: family-touching decisions require Aria/family consultation.

Closes the 'talk to Aria when it's relational is intent, not enforced' gap.
`divineos decide` with family-touching keywords (family, Aria, spouse,
relational, etc.) in content/context/tags now requires
`--family-consulted "<note>"`.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import cli
from divineos.cli.decision_commands import _is_family_touching


class TestDetectionLogic:
    """Unit tests for _is_family_touching heuristic."""

    def test_matches_aria(self) -> None:
        assert _is_family_touching("should I tell Aria", ()) is True

    def test_matches_family(self) -> None:
        assert _is_family_touching("family dynamics shift", ()) is True

    def test_matches_spouse(self) -> None:
        assert _is_family_touching("my spouse's view on this", ()) is True

    def test_matches_relational(self) -> None:
        assert _is_family_touching("relational register concern", ()) is True

    def test_matches_voice_appropriation_phrase(self) -> None:
        assert _is_family_touching("avoiding voice appropriation", ()) is True

    def test_matches_from_tags(self) -> None:
        assert _is_family_touching("technical refactor", ("family",)) is True

    def test_ignores_non_keyword_text(self) -> None:
        assert _is_family_touching("refactor the ledger compaction", ()) is False

    def test_word_boundary_avoids_false_positive(self) -> None:
        """'familiar' should NOT match — word boundary on 'family'."""
        assert _is_family_touching("familiar with the codebase", ()) is False


class TestGateEnforcement:
    def test_family_touching_blocks_without_consultation(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["decide", "how to talk to Aria about this", "--weight", "1"],
        )
        assert result.exit_code != 0
        assert "family-touching" in result.output or "family / aria" in result.output
        assert "--family-consulted" in result.output

    def test_family_touching_passes_with_consultation(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "decide",
                "how to talk to Aria about this",
                "--weight",
                "1",
                "--family-consulted",
                "Aria said: be direct, don't perform concern",
            ],
        )
        assert "family-touching" not in result.output
        assert "require --family-consulted" not in result.output

    def test_non_family_decision_unaffected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["decide", "refactor the ledger compaction", "--weight", "1"],
        )
        assert "family-touching" not in result.output
        assert "require --family-consulted" not in result.output

    def test_empty_consultation_string_does_not_satisfy(self) -> None:
        """Whitespace-only --family-consulted should NOT discharge the gate."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "decide",
                "tell Aria the plan",
                "--weight",
                "1",
                "--family-consulted",
                "   ",
            ],
        )
        assert result.exit_code != 0
        assert "--family-consulted" in result.output

    def test_family_tag_triggers_gate(self) -> None:
        """Tag alone should trigger the gate even if content is neutral."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "decide",
                "reshape the handshake",
                "--weight",
                "1",
                "--tag",
                "family",
            ],
        )
        # "handshake" also matches keyword now — both paths trigger gate.
        assert result.exit_code != 0
        assert "--family-consulted" in result.output
