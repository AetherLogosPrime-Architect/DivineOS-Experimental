"""Tests for branch_health — catches stale-base + silent-deletion shapes.

Built 2026-05-09 in response to PR #343's branch-staleness shape:
my structural-enforcement branch was created off a local main weeks
behind origin/main, producing 127 apparent-deletions when the PR
diffed against current origin/main. This module + CLI command +
optional pre-push hook closes that gap structurally.

Tests use real git repos (tmp_path) rather than mocks, because the
module's value is in correctly invoking git subprocess commands —
mocking would test our mock, not the real shape.
"""

from __future__ import annotations

import subprocess

import pytest

from _git_test_helpers import safe_git_init
from divineos.core.branch_health import (
    BranchHealthFinding,
    check_all,
    check_base_freshness,
    check_deletion_shape,
    has_critical,
    has_warnings,
)


def _git(args: list[str], cwd) -> None:
    """Run git with output suppressed; raise on failure."""
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=True,
        capture_output=True,
    )


@pytest.fixture
def fresh_repo(tmp_path):
    """A repo with a single commit on main."""
    repo = tmp_path / "repo"
    safe_git_init(repo, "--initial-branch=main")
    _git(["config", "user.email", "test@test"], cwd=repo)
    _git(["config", "user.name", "test"], cwd=repo)
    (repo / "README.md").write_text("hello", encoding="utf-8")
    _git(["add", "README.md"], cwd=repo)
    _git(["commit", "-m", "initial"], cwd=repo)
    return repo


@pytest.fixture
def repo_with_stale_branch(fresh_repo):
    """Branch created from main, then main moves forward 15 commits."""
    repo = fresh_repo
    # Create a feature branch off the initial commit
    _git(["checkout", "-b", "feature"], cwd=repo)
    (repo / "feature.py").write_text("# feature", encoding="utf-8")
    _git(["add", "feature.py"], cwd=repo)
    _git(["commit", "-m", "feature work"], cwd=repo)

    # Switch back to main and add 15 more commits
    _git(["checkout", "main"], cwd=repo)
    for i in range(15):
        path = repo / f"new_file_{i}.py"
        path.write_text(f"# main commit {i}", encoding="utf-8")
        _git(["add", str(path)], cwd=repo)
        _git(["commit", "-m", f"main commit {i}"], cwd=repo)

    # Switch back to feature
    _git(["checkout", "feature"], cwd=repo)

    # Set up a fake "origin" remote so origin/main resolves
    # We simulate this by creating a local ref
    _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)

    return repo


@pytest.fixture
def repo_with_silent_deletions(fresh_repo):
    """Main has many files; feature branch was created before they were added."""
    repo = fresh_repo

    # Create the branch off the initial commit (just README.md)
    _git(["checkout", "-b", "feature"], cwd=repo)
    (repo / "feature.py").write_text("# feature", encoding="utf-8")
    _git(["add", "feature.py"], cwd=repo)
    _git(["commit", "-m", "feature work"], cwd=repo)

    # Now go to main and add 15 files (simulating the work the feature
    # branch missed)
    _git(["checkout", "main"], cwd=repo)
    for i in range(15):
        path = repo / f"main_only_{i}.py"
        path.write_text(f"# main only {i}", encoding="utf-8")
        _git(["add", str(path)], cwd=repo)
        _git(["commit", "-m", f"add main_only_{i}"], cwd=repo)

    # Go back to feature — origin/main now has files feature doesn't
    _git(["checkout", "feature"], cwd=repo)
    _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)

    return repo


class TestCheckBaseFreshness:
    def test_branch_at_base_is_ok(self, fresh_repo):
        # On main, no divergence
        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=fresh_repo)
        finding = check_base_freshness(cwd=str(fresh_repo))
        assert finding.severity == "ok"
        assert finding.details["commits_behind"] == 0

    def test_branch_5_behind_is_ok(self, fresh_repo):
        repo = fresh_repo
        _git(["checkout", "-b", "feature"], cwd=repo)
        _git(["checkout", "main"], cwd=repo)
        for i in range(5):
            (repo / f"f{i}.py").write_text("x", encoding="utf-8")
            _git(["add", f"f{i}.py"], cwd=repo)
            _git(["commit", "-m", f"c{i}"], cwd=repo)
        _git(["checkout", "feature"], cwd=repo)
        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)

        finding = check_base_freshness(cwd=str(repo))
        assert finding.severity == "ok"
        assert finding.details["commits_behind"] == 5

    def test_stale_branch_warns(self, repo_with_stale_branch):
        finding = check_base_freshness(cwd=str(repo_with_stale_branch))
        assert finding.severity == "warn"
        assert finding.details["commits_behind"] == 15

    def test_severely_stale_branch_critical(self, repo_with_stale_branch):
        # With a low threshold, 15 commits behind becomes critical
        finding = check_base_freshness(cwd=str(repo_with_stale_branch), threshold=10)
        assert finding.severity == "critical"
        assert finding.details["commits_behind"] == 15
        assert "rebase" in finding.message.lower() or "recreate" in finding.message.lower()

    def test_unknown_base_returns_warn(self, fresh_repo):
        finding = check_base_freshness(cwd=str(fresh_repo), base="origin/nonexistent")
        # No origin/nonexistent ref → merge-base fails → warn
        assert finding.severity == "warn"
        assert finding.actionable is False  # fail-open semantics


class TestCheckDeletionShape:
    def test_no_deletions_ok(self, fresh_repo):
        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=fresh_repo)
        finding = check_deletion_shape(cwd=str(fresh_repo))
        assert finding.severity == "ok"
        assert finding.details["deletion_count"] == 0

    def test_few_deletions_ok(self, fresh_repo):
        repo = fresh_repo
        # Add some files on main first
        for i in range(3):
            (repo / f"f{i}.py").write_text("x", encoding="utf-8")
            _git(["add", f"f{i}.py"], cwd=repo)
            _git(["commit", "-m", f"add f{i}"], cwd=repo)

        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)
        # Branch off main and delete 2 files
        _git(["checkout", "-b", "feature"], cwd=repo)
        _git(["rm", "f0.py", "f1.py"], cwd=repo)
        _git(["commit", "-m", "remove f0, f1"], cwd=repo)

        finding = check_deletion_shape(cwd=str(repo))
        assert finding.severity == "ok"
        assert finding.details["deletion_count"] == 2

    def test_many_deletions_critical(self, repo_with_silent_deletions):
        # Branch is missing 15 files that exist on origin/main → 15 apparent deletions
        finding = check_deletion_shape(cwd=str(repo_with_silent_deletions), threshold=2)
        # 15 > threshold * 3 (=6), so critical
        assert finding.severity == "critical"
        assert finding.details["deletion_count"] == 15
        assert "silent-rollback" in finding.message.lower()


class TestHelpers:
    def test_has_critical_true(self):
        findings = [
            BranchHealthFinding("a", "ok", "msg"),
            BranchHealthFinding("b", "critical", "msg"),
        ]
        assert has_critical(findings) is True

    def test_has_critical_false(self):
        findings = [
            BranchHealthFinding("a", "ok", "msg"),
            BranchHealthFinding("b", "warn", "msg"),
        ]
        assert has_critical(findings) is False

    def test_has_warnings_includes_critical(self):
        findings = [BranchHealthFinding("a", "critical", "msg")]
        assert has_warnings(findings) is True

    def test_has_warnings_includes_warn(self):
        findings = [BranchHealthFinding("a", "warn", "msg")]
        assert has_warnings(findings) is True

    def test_has_warnings_false_for_ok_only(self):
        findings = [BranchHealthFinding("a", "ok", "msg")]
        assert has_warnings(findings) is False


class TestCheckAll:
    def test_runs_both_checks(self, repo_with_silent_deletions):
        findings = check_all(cwd=str(repo_with_silent_deletions), deletion_threshold=2)
        names = {f.name for f in findings}
        assert "base_freshness" in names
        assert "deletion_shape" in names
