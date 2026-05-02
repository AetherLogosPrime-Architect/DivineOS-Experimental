"""Tests for gate 4: tier-2+ decisions require a council consultation.

Closes the 'council for hard decisions is an intent, not enforced' gap.
`divineos decide --weight 2|3` now requires `--consultation CONSULT_ID`
referencing a real COUNCIL_CONSULTATION event.
"""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from divineos.cli import cli


class TestWeightOne:
    """Weight 1 (routine) decisions do not require council consultation."""

    def test_weight_1_no_consultation_required(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "minor choice", "--weight", "1"])
        assert "require --consultation" not in result.output


class TestWeightTwo:
    """Weight 2 (significant) decisions require a consultation id."""

    def test_weight_2_blocks_without_consultation(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "significant choice", "--weight", "2"])
        assert result.exit_code != 0
        assert "require --consultation" in result.output

    def test_weight_2_blocks_with_invalid_consultation(self) -> None:
        """Invalid consultation_id resolves to no payload — should block."""
        runner = CliRunner()
        with patch(
            "divineos.core.council.consultation_log._fetch_consultation_payload",
            side_effect=ValueError("not found"),
        ):
            result = runner.invoke(
                cli,
                [
                    "decide",
                    "significant choice",
                    "--weight",
                    "2",
                    "--consultation",
                    "consult-nonexistent",
                ],
            )
        assert result.exit_code != 0
        assert "No council consultation found" in result.output

    def test_weight_2_passes_with_valid_consultation(self) -> None:
        """Valid consultation id lets the decision through."""
        runner = CliRunner()
        with patch(
            "divineos.core.council.consultation_log._fetch_consultation_payload",
            return_value={"consultation_id": "consult-abc123", "question": "q"},
        ):
            result = runner.invoke(
                cli,
                [
                    "decide",
                    "significant choice",
                    "--weight",
                    "2",
                    "--consultation",
                    "consult-abc123",
                ],
            )
        assert "require --consultation" not in result.output
        assert "No council consultation found" not in result.output


class TestWeightThree:
    def test_weight_3_also_requires_consultation(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "paradigm shift", "--weight", "3"])
        assert result.exit_code != 0
        assert "require --consultation" in result.output


class TestFailOpenOnMachineryBreakage:
    def test_generic_exception_does_not_block_decision(self) -> None:
        """If consultation-log machinery raises unexpected exception,
        don't block legitimate decisions (fail-open)."""
        runner = CliRunner()
        with patch(
            "divineos.core.council.consultation_log._fetch_consultation_payload",
            side_effect=RuntimeError("db connection error"),
        ):
            result = runner.invoke(
                cli,
                [
                    "decide",
                    "significant choice",
                    "--weight",
                    "2",
                    "--consultation",
                    "consult-abc123",
                ],
            )
        assert "Consultation-log lookup failed" in result.output
