"""Tests for the correction-resolve target-verification safety gate.

Per 2026-05-18 indexing-error structural fix: position-based correction
indexing is fragile when the list mutates between operations. The
motivating pattern: I closed the wrong correction with the right
evidence because the list had silently re-indexed after a prior resolve.

This test suite pins the safety behavior so a future refactor can't
silently revert it:
1. Default mode echoes the target text + evidence and requires
   confirmation before applying the resolution.
2. ``--yes`` flag bypasses the prompt (for scripted use after
   verification).
3. Saying "no" at the prompt aborts the resolution, leaving the
   correction in its previous state.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.corrections import log_correction, open_corrections


def _setup_tmp_corrections(tmp_path: Path) -> None:
    """Log two corrections so index manipulation is meaningful."""
    log_correction("first correction — about pattern X being missed")
    log_correction("second correction — about a different shape entirely")


class TestSafetyGateDefault:
    """Default mode shows the target + evidence and requires y/n confirmation."""

    def test_default_aborts_on_no(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            # Send "n\n" as input — should abort
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "some unrelated evidence"],
                input="n\n",
            )
            assert result.exit_code == 0
            assert "aborted" in result.output.lower()
            # Both corrections still open
            opens = open_corrections()
            assert len(opens) == 2

    def test_default_resolves_on_yes(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "verified evidence"],
                input="y\n",
            )
            assert result.exit_code == 0
            assert "RESOLVED" in result.output
            # One correction now closed
            opens = open_corrections()
            assert len(opens) == 1

    def test_default_shows_target_text_in_prompt(self, tmp_path):
        """The pre-flight echo includes the target text so the agent
        can compare it against the evidence-text content."""
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "some evidence"],
                input="n\n",
            )
            # The newer correction is at index 1 (newest first)
            assert "second correction" in result.output

    def test_default_shows_evidence_preview(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "TESTEVIDENCEMARKER"],
                input="n\n",
            )
            assert "TESTEVIDENCEMARKER" in result.output


class TestSafetyGateYesFlag:
    """--yes bypasses the confirmation. Use after verification."""

    def test_yes_flag_skips_prompt(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            # No interactive input provided
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "verified evidence", "--yes"],
            )
            assert result.exit_code == 0
            assert "RESOLVED" in result.output
            # Correction was closed
            opens = open_corrections()
            assert len(opens) == 1

    def test_yes_flag_still_shows_target_echo(self, tmp_path):
        """--yes skips the prompt but still shows the target echo
        for audit-trail visibility."""
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "evidence", "--yes"],
            )
            assert "About to resolve correction" in result.output
            assert "second correction" in result.output


class TestEdgeCases:
    """Out-of-range indices and empty queues."""

    def test_out_of_range_index_rejected(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            _setup_tmp_corrections(tmp_path)
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "99", "-e", "evidence", "--yes"],
            )
            assert "out of range" in result.output.lower()
            # Both still open
            opens = open_corrections()
            assert len(opens) == 2

    def test_empty_queue_handled(self, tmp_path):
        with patch.dict("os.environ", {"DIVINEOS_DATA_HOME": str(tmp_path)}):
            # No corrections logged
            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["correction-resolve", "1", "-e", "evidence", "--yes"],
            )
            assert "no open corrections" in result.output.lower()
