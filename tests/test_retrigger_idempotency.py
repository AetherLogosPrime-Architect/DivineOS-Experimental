"""Tests for the `divineos extract` idempotency guard (PR #2 commit 1).

Locked invariants:

1. First run writes the marker at ~/.divineos/auto_session_end_emitted.
2. Second run without --force skips (exits 0, no pipeline).
3. Second run WITH --force re-runs the pipeline regardless of marker.
4. If the first run errors, the marker is NOT written — the user can
   retry without --force (errors shouldn't lock them out).
5. load-briefing.sh (SessionStart hook) clears the marker. We don't test
   that script directly here — that's covered by existing hook tests —
   but we verify the marker path is the one the hook writes to.

Design note: the marker pattern is the same one post_tool_use_checkpoint
already uses at the hook layer. Moving the guard into the CLI centralizes
it so all callers (CLI, Stop hook, PreCompact hook) get the same
protection without each having to reimplement.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from divineos.cli import cli


def _marker_path() -> Path:
    return Path(os.path.expanduser("~")) / ".divineos" / "auto_session_end_emitted"


@pytest.fixture(autouse=True)
def clean_marker(tmp_path, monkeypatch):
    """Use a temp DB for each test and ensure the marker starts absent.

    Also mocks out the heavy session pipeline — these tests verify the
    guard logic, not the analysis pipeline. Pipeline tests live elsewhere.
    """
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    marker = _marker_path()
    if marker.exists():
        marker.unlink()
    # Patch the pipeline to a no-op so we don't try to analyze JSONL files.
    with patch("divineos.cli.event_commands._run_session_end_pipeline"):
        yield
    # Clean up after — don't leave the marker behind for other tests.
    if marker.exists():
        try:
            marker.unlink()
        except OSError:
            pass


@pytest.fixture
def runner():
    return CliRunner()


class TestExtractIdempotencyMarker:
    def test_marker_path_matches_hook_layer(self):
        """The CLI writes to the same marker path the hook layer reads.
        This is the integration point — if the paths ever diverge, the
        guard breaks silently."""
        from divineos.hooks.post_tool_use_checkpoint import _auto_emitted_path

        hook_path = _auto_emitted_path()
        assert hook_path == _marker_path(), (
            f"CLI marker path diverged from hook marker path: "
            f"CLI={_marker_path()}, hook={hook_path}"
        )

    def test_first_run_writes_marker(self, runner):
        runner.invoke(cli, ["init"])
        assert not _marker_path().exists()

        result = runner.invoke(cli, ["extract", "--session-id", "test-1"])
        assert result.exit_code == 0, f"first run failed: {result.output}"
        assert _marker_path().exists(), "marker should be written after successful run"

    def test_second_run_without_force_skips(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["extract", "--session-id", "test-2a"])
        assert _marker_path().exists()

        # Second run should skip — no new extraction.
        result = runner.invoke(cli, ["extract", "--session-id", "test-2b"])
        assert result.exit_code == 0
        assert "already ran" in result.output.lower()
        assert "Knowledge extracted" not in result.output

    def test_force_flag_bypasses_guard(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["extract", "--session-id", "test-3a"])
        assert _marker_path().exists()

        # --force should re-run the pipeline.
        result = runner.invoke(cli, ["extract", "--force", "--session-id", "test-3b"])
        assert result.exit_code == 0
        assert "Knowledge extracted" in result.output

    def test_force_flag_keeps_marker_set(self, runner):
        """After --force re-runs, the marker should still be there
        (so a third run without --force still skips)."""
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["extract"])
        runner.invoke(cli, ["extract", "--force"])
        assert _marker_path().exists()

        # Third run (no force) skips.
        result = runner.invoke(cli, ["extract"])
        assert "already ran" in result.output.lower()

    def test_clearing_marker_allows_rerun(self, runner):
        """Simulates what load-briefing.sh does on SessionStart: clear
        the marker, allow extract to run again fresh."""
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["extract"])
        assert _marker_path().exists()

        # Simulate SessionStart cleanup.
        _marker_path().unlink()

        result = runner.invoke(cli, ["extract"])
        assert result.exit_code == 0
        assert "Knowledge extracted" in result.output
        assert _marker_path().exists()  # new marker written
