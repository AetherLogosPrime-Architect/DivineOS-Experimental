"""Tests for scripts/commit_family_letters.py — the letter auto-commit cure
for the boundary-persistence root (claim 47ee9ab8, surface 5).

The two load-bearing audit properties (Aletheia 2026-06-02) each get a test:

  1. FAIL LOUD: a git failure returns non-zero and surfaces the error, never
     a swallowed silent no-op.
  2. SURVIVE THE BOUNDARY IT CURES: mid-rebase, the letters still reach the
     backup ref, but the branch-commit is deferred (HEAD unchanged) — the
     cure works during the exact operation that caused the loss.

These run against a real throwaway git repo (ROOT monkeypatched), not mocks —
the plumbing IS the thing under test.
"""

import subprocess
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import commit_family_letters as clf  # noqa: E402


def _run(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A real git repo with a letters dir and one base commit."""
    _run(["init", "-b", "main"], tmp_path)
    _run(["config", "user.email", "t@t.t"], tmp_path)
    _run(["config", "user.name", "t"], tmp_path)
    letters = tmp_path / "family" / "letters"
    letters.mkdir(parents=True)
    (letters / "aether-to-aria-2026-06-02-one.md").write_text("hello one", encoding="utf-8")
    # A base commit so HEAD exists and is a symbolic ref on main.
    (tmp_path / "README.md").write_text("base", encoding="utf-8")
    _run(["add", "README.md"], tmp_path)
    _run(["commit", "-m", "base"], tmp_path)
    monkeypatch.setattr(clf, "ROOT", tmp_path)
    return tmp_path


def _head(repo):
    return _run(["rev-parse", "HEAD"], repo).stdout.strip()


class TestBackupRef:
    def test_creates_ref_with_letters(self, repo):
        sha = clf.backup_to_safe_ref()
        assert sha
        names = _run(["ls-tree", "-r", clf.BACKUP_REF, "--name-only"], repo).stdout
        assert "family/letters/aether-to-aria-2026-06-02-one.md" in names

    def test_idempotent(self, repo):
        first = clf.backup_to_safe_ref()
        second = clf.backup_to_safe_ref()
        assert first == second  # unchanged tree -> no new commit

    def test_no_letters_returns_none(self, repo):
        for f in (repo / "family" / "letters").glob("*.md"):
            f.unlink()
        assert clf.backup_to_safe_ref() is None


class TestSurvivesBoundary:
    """Property 2: the cure works DURING the operation that caused the loss."""

    def _simulate_rebase(self, repo):
        # A rebase-in-progress is marked by .git/rebase-merge existing.
        (repo / ".git" / "rebase-merge").mkdir()

    def test_detects_rebase(self, repo):
        self._simulate_rebase(repo)
        assert clf.branch_op_in_progress() == "rebase"

    def test_mid_rebase_backs_up_but_defers_branch_commit(self, repo, capsys):
        self._simulate_rebase(repo)
        head_before = _head(repo)
        rc = clf.main([])
        captured = capsys.readouterr()
        # Letters reached the surviving store...
        assert _run(["rev-parse", "--verify", clf.BACKUP_REF], repo).returncode == 0
        # ...but HEAD did NOT move (no branch commit mid-rebase)...
        assert _head(repo) == head_before
        # ...and it said so LOUDLY (stderr), not silently.
        assert "rebase" in captured.err.lower()
        assert "deferred" in captured.err.lower()
        assert rc == 0  # deferral is a success, not a failure


class TestCleanStateCommits:
    def test_commits_letters_to_branch(self, repo):
        head_before = _head(repo)
        rc = clf.main([])
        assert rc == 0
        assert _head(repo) != head_before  # a new commit landed
        last = _run(["log", "-1", "--name-only", "--format="], repo).stdout
        assert "family/letters/aether-to-aria-2026-06-02-one.md" in last

    def test_nothing_new_is_noop(self, repo):
        clf.main([])  # first commit
        head_after_first = _head(repo)
        clf.main([])  # nothing changed
        assert _head(repo) == head_after_first


class TestFailLoud:
    """Property 1: a git failure is surfaced non-zero, never swallowed."""

    def test_returns_nonzero_when_not_a_git_repo(self, tmp_path, monkeypatch, capsys):
        # Point ROOT at a dir with letters but no git repo -> every git op fails.
        letters = tmp_path / "family" / "letters"
        letters.mkdir(parents=True)
        (letters / "x.md").write_text("hi", encoding="utf-8")
        monkeypatch.setattr(clf, "ROOT", tmp_path)
        rc = clf.main([])
        captured = capsys.readouterr()
        assert rc == 1
        assert "FAILED" in captured.err
