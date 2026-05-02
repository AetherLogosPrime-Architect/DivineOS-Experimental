"""Tests for the post-sleep auto-extract trigger (PR #2 commit 3).

Closes claim 36a41eb0 (creative recombinations were ephemeral). After
a full sleep cycle, `divineos sleep` now auto-runs `divineos extract --force`
so phase-5 connections land in the knowledge store instead of evaporating.

Locked invariants:

1. After a successful full-cycle sleep, `divineos extract --force` runs.
2. --force is used so the post-sleep extract works even if the user
   already ran extract earlier in the session.
3. Dry-run mode skips the auto-extract (user asked to preview, not commit).
4. Single-phase mode skips the auto-extract (user asked for one phase,
   not the full consolidation-worthy cycle).
5. If the extract subprocess fails, sleep still completes successfully —
   the sleep work is valuable on its own, extract is additive.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    marker = Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass
    yield
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


@pytest.fixture
def runner():
    return CliRunner()


class TestPostSleepExtractTrigger:
    def test_full_sleep_cycle_calls_extract_with_force(self, runner):
        """The load-bearing invariant: sleep triggers extract --force."""
        runner.invoke(cli, ["init"])
        with patch("subprocess.run") as mock_run:
            result = runner.invoke(cli, ["sleep", "--skip-maintenance"])
        assert result.exit_code == 0

        # Find the extract call among subprocess invocations.
        extract_calls = [
            c
            for c in mock_run.call_args_list
            if c.args
            and len(c.args[0]) >= 2
            and c.args[0][0] == "divineos"
            and c.args[0][1] == "extract"
        ]
        assert len(extract_calls) == 1, (
            f"expected exactly one `divineos extract` call, got {len(extract_calls)}"
        )
        assert "--force" in extract_calls[0].args[0], (
            "post-sleep extract must pass --force so it runs even if marker exists"
        )

    def test_dry_run_does_NOT_trigger_extract(self, runner):
        """Dry-run preview should not spawn extract."""
        runner.invoke(cli, ["init"])
        with patch("subprocess.run") as mock_run:
            result = runner.invoke(cli, ["sleep", "--dry-run"])
        assert result.exit_code == 0

        extract_calls = [
            c
            for c in mock_run.call_args_list
            if c.args
            and len(c.args[0]) >= 2
            and c.args[0][0] == "divineos"
            and c.args[0][1] == "extract"
        ]
        assert len(extract_calls) == 0

    def test_single_phase_does_NOT_trigger_extract(self, runner):
        """Single-phase mode is narrow work, not consolidation-worthy."""
        runner.invoke(cli, ["init"])
        with patch("subprocess.run") as mock_run:
            result = runner.invoke(cli, ["sleep", "--phase", "pruning"])
        assert result.exit_code == 0

        extract_calls = [
            c
            for c in mock_run.call_args_list
            if c.args
            and len(c.args[0]) >= 2
            and c.args[0][0] == "divineos"
            and c.args[0][1] == "extract"
        ]
        assert len(extract_calls) == 0

    def test_extract_failure_does_NOT_fail_sleep(self, runner):
        """Sleep must complete successfully even if extract subprocess errors."""
        runner.invoke(cli, ["init"])

        def _fail_on_extract(cmd, *a, **kw):
            from unittest.mock import MagicMock

            if cmd and len(cmd) >= 2 and cmd[0] == "divineos" and cmd[1] == "extract":
                raise OSError("simulated extract failure")
            return MagicMock(returncode=0, stdout=b"", stderr=b"")

        with patch("subprocess.run", side_effect=_fail_on_extract):
            result = runner.invoke(cli, ["sleep", "--skip-maintenance"])
        assert result.exit_code == 0
        assert "failed" in result.output.lower() or "extraction failed" in result.output.lower()
