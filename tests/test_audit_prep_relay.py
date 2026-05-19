"""Tests for divineos audit prep-relay — upstream-of-Finding-75 gate.

The describe-then-CONFIRMS pattern recurred for the 4th time in one
arc on 2026-05-18: Aletheia caught me composing an audit-relay message
about 8 commits that were local-only. Finding 75's gate operates
correctly at the round-filing layer, but the same pattern recurs
one layer earlier at relay-message composition.

prep-relay closes that gap. It verifies that named commits are
reachable on the remote-branch BEFORE producing a relay template.
If any aren't pushed, it refuses with the list of unreachable SHAs.

These tests use a real temporary git repo with a fake "remote"
(another local repo) so the verification path is exercised end-to-end,
not just mocked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from click.testing import CliRunner

from divineos.cli import cli


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command in cwd. Fails loudly on non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (cwd={cwd}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def _setup_local_with_fake_remote(tmp_path: Path) -> tuple[Path, Path]:
    """Create a local repo with a 'remote' that's actually another local repo.

    Returns (local_path, remote_path).
    """
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    remote.mkdir()
    local.mkdir()

    # Initialize bare remote
    _git(remote, "init", "--bare", "-b", "main")

    # Initialize local
    _git(local, "init", "-b", "main")
    _git(local, "config", "user.email", "test@test")
    _git(local, "config", "user.name", "Test")
    _git(local, "remote", "add", "origin", str(remote))

    # Initial commit + push
    (local / "README.md").write_text("initial\n")
    _git(local, "add", "README.md")
    _git(local, "commit", "-m", "initial commit")
    _git(local, "push", "-u", "origin", "main")

    return local, remote


class TestPrepRelayBasics:
    """The prep-relay command exists and shows help."""

    def test_command_registered(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "prep-relay", "--help"])
        assert result.exit_code == 0
        assert "prep-relay" in result.output.lower() or "describe-then-CONFIRMS" in result.output

    def test_help_mentions_finding_75(self):
        """The help text should name the structural lineage so future-
        readers know why this gate exists."""
        runner = CliRunner()
        result = runner.invoke(cli, ["audit", "prep-relay", "--help"])
        assert result.exit_code == 0
        # Mentions either Finding 75 or describe-then-CONFIRMS
        out = result.output
        assert "Finding 75" in out or "describe-then-CONFIRMS" in out


class TestPrepRelayBlocksUnpushedCommits:
    """The core gate: prep-relay refuses to produce a relay-template if
    any commit in the range is not reachable on the remote-branch."""

    def test_refuses_when_commits_are_unpushed(self, tmp_path, monkeypatch):
        local, _remote = _setup_local_with_fake_remote(tmp_path)
        # Make a local commit without pushing
        (local / "added.md").write_text("new content\n")
        _git(local, "add", "added.md")
        _git(local, "commit", "-m", "feat: local-only commit not yet pushed")

        # cd into the local repo so divineos sees this as cwd
        monkeypatch.chdir(local)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "prep-relay",
                "--range",
                "origin/main..HEAD",
                "--branch",
                "main",
            ],
        )
        assert result.exit_code == 1, (
            f"Expected exit 1 (blocked); got {result.exit_code}. Output:\n{result.output}"
        )
        assert "BLOCKED" in result.output
        assert "not reachable" in result.output.lower()
        assert "local-only commit" in result.output

    def test_passes_when_all_commits_are_pushed(self, tmp_path, monkeypatch):
        local, _remote = _setup_local_with_fake_remote(tmp_path)
        # Make a commit and push it
        (local / "added.md").write_text("pushed content\n")
        _git(local, "add", "added.md")
        _git(local, "commit", "-m", "feat: pushed commit visible on remote")
        _git(local, "push", "origin", "main")

        monkeypatch.chdir(local)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "prep-relay",
                "--range",
                "origin/main~1..HEAD",
                "--branch",
                "main",
            ],
        )
        assert result.exit_code == 0, (
            f"Expected exit 0 (verified); got {result.exit_code}. Output:\n{result.output}"
        )
        assert "verified" in result.output.lower()
        assert "AUDIT RELAY TEMPLATE" in result.output
        assert "pushed commit" in result.output


class TestPrepRelayEmptyRange:
    """When the range is empty, command exits cleanly with a 'nothing to relay' message."""

    def test_empty_range_handled(self, tmp_path, monkeypatch):
        local, _remote = _setup_local_with_fake_remote(tmp_path)
        monkeypatch.chdir(local)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "audit",
                "prep-relay",
                "--range",
                "origin/main..HEAD",
                "--branch",
                "main",
            ],
        )
        assert result.exit_code == 0
        assert "No commits in range" in result.output or "Nothing to audit-relay" in result.output


class TestFinding79NarrowRangeBypass:
    """Finding 79 (Aletheia 2026-05-18): prep-relay's --range parameter
    is operator-chosen and was previously trusted. The narrow-range bypass:
    --range HEAD~1..HEAD where HEAD is pushed but HEAD~1 isn't — only
    HEAD gets checked; HEAD~1's unpushed substance can be described in
    surrounding prose with plausible deniability.

    The fix-shape Aletheia named: emit a warning when --range doesn't
    cover the full set of commits between remote-branch and HEAD.
    Discipline-shape: surface, don't force. The warning makes the
    scoping-narrow shape visible in stdout."""

    def test_narrow_range_emits_warning_when_unscoped_commits_exist(self, tmp_path, monkeypatch):
        """Reproduce the narrow-range bypass empirically: create 3
        unpushed commits, scope --range to only the latest one (HEAD~0),
        verify the warning fires naming the unscoped commits."""
        local, _remote = _setup_local_with_fake_remote(tmp_path)

        # Create 3 unpushed commits on top of the initial pushed commit
        for i in range(1, 4):
            (local / f"file-{i}.md").write_text(f"content {i}\n")
            _git(local, "add", f"file-{i}.md")
            _git(local, "commit", "-m", f"feat: local commit {i}")

        # Push only the first of these (leaves 2 unpushed)
        _git(local, "push", "origin", "main~2:main")

        monkeypatch.chdir(local)
        runner = CliRunner()
        # Narrow range: only HEAD (the latest commit)
        result = runner.invoke(
            cli,
            [
                "audit",
                "prep-relay",
                "--range",
                "HEAD~1..HEAD",
                "--branch",
                "main",
            ],
        )
        # Per Finding 79 retrofit 2026-05-18 evening (laziest-person
        # heuristic): narrow --range that misses unpushed commits now
        # BLOCKS by default instead of warning. The block message names
        # the unscoped commits and points at the named-bypass env var.
        assert ("BLOCKED" in result.output) or ("Warning" in result.output), (
            f"Expected Finding 79 gate output (block or warning shape); output:\n{result.output}"
        )
        assert "Finding 79" in result.output or "not in --range" in result.output, (
            f"Expected Finding 79 lineage explanation; output:\n{result.output}"
        )

    def test_full_range_does_not_emit_unscoped_warning(self, tmp_path, monkeypatch):
        """When --range covers the full unpushed set, no Finding 79 warning."""
        local, _remote = _setup_local_with_fake_remote(tmp_path)
        # Create 1 unpushed commit then push it
        (local / "added.md").write_text("content\n")
        _git(local, "add", "added.md")
        _git(local, "commit", "-m", "feat: full-scope commit")
        _git(local, "push", "origin", "main")

        monkeypatch.chdir(local)
        runner = CliRunner()
        # Full range covers the pushed commit
        result = runner.invoke(
            cli,
            [
                "audit",
                "prep-relay",
                "--range",
                "origin/main~1..HEAD",
                "--branch",
                "main",
            ],
        )
        assert result.exit_code == 0
        # No "additional commit(s)" warning expected
        assert "additional commit" not in result.output, (
            f"Full-coverage range should not trigger Finding 79 warning; output:\n{result.output}"
        )
