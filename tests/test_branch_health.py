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
    _settle_freshness_against_deletions,
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
        # Files must have UNIQUE content so the content-hash presence
        # check correctly identifies each as a distinct deletion. Under
        # the new semantic (2026-07-14 Aletheia), identical-content
        # files share a blob and deleting a duplicate doesn't count as
        # destruction because the content still lives in the remaining
        # copy. Real content-destruction requires unique content.
        for i in range(3):
            (repo / f"f{i}.py").write_text(f"unique content for file {i}\n" * 5, encoding="utf-8")
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

    def test_many_deletions_critical(self, fresh_repo):
        """A branch that REMOVES many files present at the fork is critical.

        Rewritten 2026-08-30. This test used to run on the stale-base fixture
        and assert critical, which pinned the bug rather than the behaviour:
        that fixture builds a branch which deletes NOTHING. Its own docstring
        says so -- "feature branch was created before they were added" -- and
        its comment called the count "apparent".

        Not argued, measured. Rebuilt the fixture's exact situation and asked
        each instrument: two-dot said 15 deleted, three-dot said 0, and
        performing the merge without committing also said 0. A branch cannot
        remove a file it never had.

        So this test now builds a branch that genuinely destroys content --
        the files exist at the fork and the branch removes them -- which is
        the shape the check was always described as catching, and the shape
        the fixture below never produced.
        """
        repo = fresh_repo
        for i in range(15):
            (repo / f"doomed_{i}.py").write_text(f"unique content {i}\n" * 5, encoding="utf-8")
            _git(["add", f"doomed_{i}.py"], cwd=repo)
            _git(["commit", "-m", f"add doomed_{i}"], cwd=repo)
        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)

        _git(["checkout", "-b", "feature"], cwd=repo)
        _git(["rm"] + [f"doomed_{i}.py" for i in range(15)], cwd=repo)
        _git(["commit", "-m", "remove all fifteen"], cwd=repo)

        finding = check_deletion_shape(cwd=str(repo), threshold=2)
        assert finding.severity == "critical"
        assert finding.details["deletion_count"] == 15
        assert "silent-rollback" in finding.message.lower()

    def test_stale_base_is_not_a_deletion(self, repo_with_silent_deletions):
        """The must-NOT-fire half, and the reason the check was wrong.

        Main gained fifteen files after the branch forked. The branch never
        saw them, so it never removed them, and a real merge deletes nothing.
        Two-dot calls that fifteen deletions because it only knows
        present-here, absent-there.

        This blocked a real push on 2026-08-30 claiming twenty-three
        deletions on a branch that would delete zero, and it is the same
        instrument fault Aether settled the same day on nine.
        """
        finding = check_deletion_shape(cwd=str(repo_with_silent_deletions), threshold=2)
        assert finding.severity == "ok"
        assert finding.details["deletion_count"] == 0

    def test_renames_not_counted_as_deletions(self, fresh_repo):
        """2026-07-14 Aletheia audit fix: a file MOVED from A to B is a
        rename, not a deletion. The guard must use --find-renames so
        archive-relocations and folder-reorgs don't trigger the false-
        alarm. Mispriced toll trains reach-for-bypass; correctly priced
        toll stays cheap for the honest act."""
        repo = fresh_repo
        # Create 10 files on main
        for i in range(10):
            (repo / f"doc_{i}.md").write_text(
                f"substantive content in doc {i}\n" * 20, encoding="utf-8"
            )
            _git(["add", f"doc_{i}.md"], cwd=repo)
            _git(["commit", "-m", f"add doc_{i}"], cwd=repo)

        _git(["update-ref", "refs/remotes/origin/main", "main"], cwd=repo)
        # Branch off main and MOVE all 10 to archive/ subfolder
        _git(["checkout", "-b", "archive-sweep"], cwd=repo)
        (repo / "archive").mkdir()
        for i in range(10):
            (repo / f"doc_{i}.md").rename(repo / "archive" / f"doc_{i}.md")
        _git(["add", "-A"], cwd=repo)
        _git(["commit", "-m", "archive-move all docs"], cwd=repo)

        finding = check_deletion_shape(cwd=str(repo))
        # With --find-renames, git detects these as renames (status R)
        # not deletions (status D). Guard should see 0 deletions.
        assert finding.severity == "ok", (
            f"Archive-moves must not trigger the deletion guard. "
            f"Got severity={finding.severity!r}, "
            f"deletion_count={finding.details.get('deletion_count')}"
        )
        assert finding.details["deletion_count"] == 0


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

    def test_returns_both_findings_in_order(self, repo_with_silent_deletions):
        findings = check_all(cwd=str(repo_with_silent_deletions), deletion_threshold=2)
        assert [f.name for f in findings] == ["base_freshness", "deletion_shape"]


class TestFreshnessSettledByDeletions:
    """base_freshness predicts apparent deletions; deletion_shape measures them.

    A critical staleness verdict standing beside a measured zero is the gate
    blocking on its own guess while the answer sits next to it. These pin the
    settling in BOTH directions: the downgrade must never fire on anything
    other than a confirmed zero.
    """

    def _stale_critical(self) -> BranchHealthFinding:
        return BranchHealthFinding(
            name="base_freshness",
            severity="critical",
            message="Branch is 13 commit(s) behind origin/main (threshold 5).",
            actionable=True,
            details={"commits_behind": 13},
        )

    def test_measured_zero_downgrades_to_warn(self):
        settled = _settle_freshness_against_deletions(
            self._stale_critical(),
            BranchHealthFinding(
                name="deletion_shape",
                severity="ok",
                message="No files would be deleted by merge.",
                details={"deletion_count": 0},
            ),
        )
        assert settled.severity == "warn"
        assert settled.details["commits_behind"] == 13
        assert settled.details["settled_by"] == "deletion_shape"
        assert "13 commit(s) behind" in settled.message

    def test_could_not_measure_leaves_the_block(self):
        """The exact fault this family is about: an unrun check is not a clean
        one. deletion_shape returns warn with no count when git fails."""
        settled = _settle_freshness_against_deletions(
            self._stale_critical(),
            BranchHealthFinding(
                name="deletion_shape",
                severity="warn",
                message="Could not compute deletion shape vs origin/main: boom.",
            ),
        )
        assert settled.severity == "critical"

    def test_nonzero_within_tolerance_leaves_the_block(self):
        """An `ok` severity is not enough on its own. A small real deletion
        count is still the harm the freshness check exists to predict."""
        settled = _settle_freshness_against_deletions(
            self._stale_critical(),
            BranchHealthFinding(
                name="deletion_shape",
                severity="ok",
                message="3 file(s) would be deleted by merge. Within tolerance.",
                details={"deletion_count": 3},
            ),
        )
        assert settled.severity == "critical"

    def test_real_deletions_leave_the_block(self):
        settled = _settle_freshness_against_deletions(
            self._stale_critical(),
            BranchHealthFinding(
                name="deletion_shape",
                severity="critical",
                message="40 file(s) would be deleted by merge.",
                details={"deletion_count": 40},
            ),
        )
        assert settled.severity == "critical"

    def test_a_warn_freshness_is_returned_untouched(self):
        original = BranchHealthFinding(
            name="base_freshness",
            severity="warn",
            message="Branch is 2 commit(s) behind origin/main.",
            details={"commits_behind": 2},
        )
        settled = _settle_freshness_against_deletions(
            original,
            BranchHealthFinding(
                name="deletion_shape",
                severity="ok",
                message="No files would be deleted by merge.",
                details={"deletion_count": 0},
            ),
        )
        assert settled is original
