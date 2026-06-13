"""Tests for `divineos audit prepare-artifact` (audit_artifact_commands).

This command shipped without tests in the consolidate-2026-06-01 snapshot —
decomposing the blob into focused units surfaced the gap. These exercise the
real command against real throwaway git repos (no mocks): the dry-run path
(local: tree-hash + slug, no side effects), the no-staged-changes guard, and
the full path against a local bare remote (commit-tree + push to
refs/audit/<slug>).
"""

import subprocess
import sys
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from _git_test_helpers import safe_git_init


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from divineos.cli import audit_artifact_commands  # noqa: E402


def _git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _make_cli() -> click.Group:
    """Minimal cli with an 'audit' group, then register prepare-artifact onto it."""
    cli = click.Group()
    cli.add_command(click.Group("audit"))
    audit_artifact_commands.register(cli)
    return cli


@pytest.fixture
def repo(tmp_path, monkeypatch):
    _git(["init", "-b", "main"], tmp_path)
    _git(["config", "user.email", "t@t.t"], tmp_path)
    _git(["config", "user.name", "t"], tmp_path)
    (tmp_path / "f.txt").write_text("base", encoding="utf-8")
    _git(["add", "f.txt"], tmp_path)
    _git(["commit", "-m", "base"], tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


class TestRegistration:
    def test_requires_audit_group_first(self):
        # register must fail loud if the 'audit' group isn't there yet.
        bare = click.Group()
        with pytest.raises(RuntimeError):
            audit_artifact_commands.register(bare)


class TestNoStagedChanges:
    def test_errors_when_nothing_staged(self, repo):
        result = CliRunner().invoke(_make_cli(), ["audit", "prepare-artifact", "--dry-run"])
        assert result.exit_code != 0
        assert "No staged changes" in result.output


class TestDryRun:
    def test_prints_treehash_and_ref_no_side_effects(self, repo):
        (repo / "g.txt").write_text("staged change", encoding="utf-8")
        _git(["add", "g.txt"], repo)
        result = CliRunner().invoke(_make_cli(), ["audit", "prepare-artifact", "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "tree-hash:" in result.output
        assert "refs/audit/" in result.output
        # No audit ref created (dry-run has no side effects).
        refs = _git(["for-each-ref", "refs/audit/"], repo).stdout
        assert refs.strip() == ""


class TestFullPathToLocalRemote:
    def test_pushes_orphan_commit_to_audit_ref(self, tmp_path, monkeypatch):
        # A local bare remote stands in for origin.
        bare = tmp_path / "remote.git"
        safe_git_init(bare, "--bare")
        work = tmp_path / "work"
        safe_git_init(work, "-b", "main")
        _git(["config", "user.email", "t@t.t"], work)
        _git(["config", "user.name", "t"], work)
        (work / "f.txt").write_text("base", encoding="utf-8")
        _git(["add", "f.txt"], work)
        _git(["commit", "-m", "base"], work)
        _git(["remote", "add", "origin", str(bare)], work)
        _git(["push", "origin", "main"], work)
        # Stage a change to bind.
        (work / "g.txt").write_text("guardrail change", encoding="utf-8")
        _git(["add", "g.txt"], work)
        monkeypatch.chdir(work)

        result = CliRunner().invoke(
            _make_cli(), ["audit", "prepare-artifact", "--slug", "testslug"]
        )
        assert result.exit_code == 0, result.output
        # The audit ref now exists on the bare remote, artifact-only.
        remote_refs = _git(["for-each-ref", "refs/audit/"], bare).stdout
        assert "refs/audit/testslug" in remote_refs
