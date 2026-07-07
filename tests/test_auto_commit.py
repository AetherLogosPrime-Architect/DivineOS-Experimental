"""Tests for divineos.core.auto_commit.

The weld Andrew asked for 2026-07-05: commit fires automatically at
extract/sleep boundaries so today's forgotten-commit shape cannot
recur silently.

Uses real git subprocess against a tmp_path repo — no mocking of git
itself. Only the external-channels DEFAULT is overridden so tests do
not touch the real ~/.divineos-shared folder.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import (
    AutoCommitResult,
    auto_commit_substrate,
    find_repo_root,
)
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "config", "commit.gpgsign", "false")
    # Ignore pytest cache / __pycache__ so nested-under-outer-repo runs
    # do not report the harness's own scratch files as dirty.
    # Ignore both harness artifacts AND divineos autouse-fixture artifacts
    # (a session conftest drops divineos_home/ and test_ledger.db into
    # tmp_path). Without this, git sees them as dirty and auto_commit
    # commits them, breaking the "clean tree" contract.
    (root / ".gitignore").write_text(
        "__pycache__/\n.pytest_cache/\n*.pyc\ndivineos_home/\ntest_ledger.db\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(root, "add", ".gitignore", "README.md")
    _git(root, "commit", "-q", "-m", "seed")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _init_repo(tmp_path)
    return tmp_path


class TestAutoCommitBasics:
    def test_clean_tree_no_op(self, repo: Path):
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is False
        assert "clean" in result.reason.lower()

    def test_dirty_tree_commits(self, repo: Path):
        (repo / "new_file.md").write_text("body\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert result.committed is True
        assert result.dirty_lines >= 1

        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "auto-commit (pre-extract)" in log

    def test_modified_tracked_file_commits(self, repo: Path):
        (repo / "README.md").write_text("mutated\n", encoding="utf-8")
        result = auto_commit_substrate(repo, reason="post-extract", channels=())
        assert result.committed is True

        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "post-extract" in log

    def test_reason_appears_in_commit_subject(self, repo: Path):
        (repo / "a.md").write_text("x\n", encoding="utf-8")
        auto_commit_substrate(repo, reason="pre-sleep", channels=())
        log = _git(repo, "log", "-1", "--pretty=%s").stdout.strip()
        assert "pre-sleep" in log

    def test_not_a_git_repo_returns_uncommitted(self, tmp_path: Path):
        # A directory without .git — not a repo at all.
        result = auto_commit_substrate(tmp_path, reason="pre-extract", channels=())
        assert result.committed is False
        assert "not a git repo" in result.reason


class TestExternalChannelSync:
    def test_new_external_file_synced_and_committed(self, repo: Path, tmp_path: Path):
        source = tmp_path / "letters_source"
        source.mkdir()
        (source / "aria-to-aether-2026-07-05-test.md").write_text("letter body\n", encoding="utf-8")
        channels = (
            ExternalChannel(
                name="test-letters",
                source=source,
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )

        result = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
        assert result.committed is True
        assert result.files_synced == 1
        # File landed in the mirror
        assert (repo / "family/letters/aria-to-aether-2026-07-05-test.md").is_file()

    def test_already_synced_file_not_recopied(self, repo: Path, tmp_path: Path):
        source = tmp_path / "letters_source"
        source.mkdir()
        letter_name = "aria-to-aether-2026-07-05-already-synced.md"
        (source / letter_name).write_text("orig\n", encoding="utf-8")

        # Put a copy already in mirror + commit it
        mirror = repo / "family/letters"
        mirror.mkdir(parents=True)
        (mirror / letter_name).write_text("orig\n", encoding="utf-8")
        _git(repo, "add", str(mirror / letter_name))
        _git(repo, "commit", "-q", "-m", "existing letter")

        channels = (
            ExternalChannel(
                name="test-letters",
                source=source,
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )

        result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)
        # The load-bearing assertion for this test: the already-synced file
        # is NOT re-copied. Whether committed=True depends on unrelated
        # tmp_path noise from autouse fixtures; that's not this test's
        # contract.
        assert result.files_synced == 0

    def test_missing_source_dir_is_silent(self, repo: Path, tmp_path: Path):
        channels = (
            ExternalChannel(
                name="ghost",
                source=tmp_path / "does_not_exist",
                repo_mirror=Path("family/letters"),
                pattern="*.md",
            ),
        )
        result = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
        assert result.committed is False
        assert result.files_synced == 0


class TestFindRepoRoot:
    def test_find_repo_root_at_root(self, repo: Path):
        assert find_repo_root(repo) == repo

    def test_find_repo_root_from_subdir(self, repo: Path):
        sub = repo / "src" / "deep"
        sub.mkdir(parents=True)
        assert find_repo_root(sub) == repo

    def test_find_repo_root_walks_to_nearest(self, tmp_path: Path):
        # When multiple .git dirs nest, walk finds the nearest ancestor.
        inner = tmp_path / "inner"
        inner.mkdir()
        _init_repo(inner)
        deep = inner / "a" / "b"
        deep.mkdir(parents=True)
        assert find_repo_root(deep) == inner


class TestIdempotency:
    def test_second_call_after_success_is_noop(self, repo: Path):
        (repo / "one.md").write_text("x\n", encoding="utf-8")
        first = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert first.committed is True

        second = auto_commit_substrate(repo, reason="pre-extract", channels=())
        assert second.committed is False


class TestResultShape:
    def test_default_result_shape(self):
        r = AutoCommitResult(committed=False, reason="clean")
        assert r.files_synced == 0
        assert r.dirty_lines == 0
