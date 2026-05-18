"""Tests for Aletheia Finding 75: audit-round CLI requires --source-ref.

The describe-then-CONFIRMS pattern (filing audit rounds for unpushed
substance) recurred three times in one arc on 2026-05-17, producing
ratification-of-claim instead of honest verification. Substrate-level
fix: round-creation refuses to proceed without --source-ref naming the
branch the audited substance lives on, AND the branch must be reachable
locally (git rev-parse --verify). An explicit --no-source-ref flag
exists for rounds with no code substance (relational findings, tracked
obligations); its use is annotated in the round notes.
"""

from __future__ import annotations

import subprocess
import sys

from click.testing import CliRunner

from divineos.cli import cli


def _is_in_git_repo() -> bool:
    """True if pytest is running inside a real git working tree."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            text=True,
            check=False,
        )
        return r.returncode == 0
    except OSError:
        return False


class TestSourceRefRequired:
    """The gate refuses round-creation without --source-ref or --no-source-ref."""

    def test_no_flag_at_all_is_blocked(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["audit", "submit-round", "test focus", "--actor", "user"],
        )
        assert result.exit_code != 0
        assert "source-ref" in result.output.lower() or "source-ref" in str(result.exception or "")

    def test_no_source_ref_bypass_works(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (bypass)",
                "--actor",
                "user",
                "--no-source-ref",
            ],
        )
        # Either succeeds (round created) or fails for unrelated DB reasons —
        # the key assertion is the gate does NOT fire on this path.
        if result.exit_code != 0:
            assert "source-ref" not in result.output.lower()

    def test_invalid_source_ref_is_blocked(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (invalid ref)",
                "--actor",
                "user",
                "--source-ref",
                "this-branch-does-not-exist-anywhere-zzz",
            ],
        )
        assert result.exit_code != 0
        assert "not reachable" in result.output.lower() or "not reachable" in str(
            result.exception or ""
        )

    def test_valid_source_ref_passes_gate(self):
        """If we're in a git repo with HEAD reachable, HEAD itself is a valid ref."""
        if not _is_in_git_repo():
            return  # skip; not in git repo
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (valid ref)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
            ],
        )
        # Gate should pass — round creation may still fail for unrelated
        # DB reasons during test isolation, but the gate-block message
        # should NOT appear.
        gate_block_text = "is not reachable"
        assert gate_block_text not in result.output


class TestAnnotation:
    """The round's notes carry an honest annotation of which path was used."""

    def test_source_ref_annotation_in_output(self):
        """When --source-ref is used, the CLI prints the binding."""
        if not _is_in_git_repo():
            return
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "submit-round",
                "test focus (annotation)",
                "--actor",
                "user",
                "--source-ref",
                "HEAD",
            ],
        )
        # Output (if successful) names the source ref
        if result.exit_code == 0:
            assert "Source ref: HEAD" in result.output


class TestHelpTextMentionsFinding(object):
    """The --help output should name Finding 75 so future-readers know why."""

    def test_help_names_finding_75(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "submit-round", "--help"])
        assert result.exit_code == 0
        assert "Finding 75" in result.output or "describe-then-CONFIRMS" in result.output
