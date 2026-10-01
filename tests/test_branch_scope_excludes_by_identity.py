"""The scan must not count the branch under test as somewhere else.

2026-09-16. A push was refused over eleven archive exports, with the message
that every one of them exists on another ref at the same bytes and none are
unique here. Checked by hand: not one existed anywhere else. Following the
rebuild instruction would have destroyed the only copies.

THE CAUSE, and it is one line above the comparison that documents fixing this
exact class. The exclusion set was built by resolving the branch to a short
name and pasting it into two strings. The push gate invokes this with a COMMIT
identifier, git returns an empty short name for a commit, and the two refs
constructed were a bare prefix with nothing after them. Neither exists, nothing
was excluded, and the branch matched its own blobs on every file.

So the sibling suite passes while production fails, because every test there
hands it a plain branch name and nothing in the house ever did.

These run the script the way the gate runs it.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCOPE = _PROJECT_ROOT / "scripts" / "check_branch_scope.py"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    shutil.copy2(_SCOPE, root / "scripts" / _SCOPE.name)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    return root


def _branch_with_unique_file(root: Path) -> None:
    _git(root, "checkout", "-q", "main")
    _git(root, "checkout", "-q", "-B", "work")
    target = root / "dreams" / "aether" / "only_copy.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("the only copy of this\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "add the only copy")


def _run(root: Path, revision: str) -> str:
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "check_branch_scope.py"), revision],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    return proc.stdout


class TestTheVerdictDoesNotDependOnHowTheBranchIsSpelled:
    def test_a_branch_name_reports_the_file_as_unique(self, repo: Path) -> None:
        """The spelling every existing test uses, kept as the control. Without
        it a regression here would look like the bug moving rather than the
        fix working."""
        _branch_with_unique_file(repo)
        assert "ONLY HERE" in _run(repo, "work")

    def test_a_commit_identifier_reports_the_file_as_unique(self, repo: Path) -> None:
        """THE ONE THAT WAS MISSING, and the only spelling production uses.

        Before the fix this said the file exists on another ref at the same
        bytes -- because the other ref it found was the branch itself.
        """
        _branch_with_unique_file(repo)
        sha = _git(repo, "rev-parse", "HEAD")
        assert "ONLY HERE" in _run(repo, sha)

    def test_the_two_spellings_agree(self, repo: Path) -> None:
        """Asserted directly rather than inferred from the two above, because
        the defect was precisely that they disagreed while each looked fine
        from inside its own test."""
        _branch_with_unique_file(repo)
        sha = _git(repo, "rev-parse", "HEAD")
        by_name = "ONLY HERE" in _run(repo, "work")
        by_sha = "ONLY HERE" in _run(repo, sha)
        assert by_name == by_sha


class TestARealCopyElsewhereIsStillCleared:
    """The fix must not turn every file into a unique one. Over-excluding
    reads as caution and is the gate losing its ability to clear anything."""

    def test_a_file_on_another_branch_is_not_called_unique(self, repo: Path) -> None:
        _git(repo, "checkout", "-q", "main")
        _git(repo, "checkout", "-q", "-B", "keeper")
        kept = repo / "family" / "letters" / "kept.md"
        kept.parent.mkdir(parents=True, exist_ok=True)
        kept.write_text("body\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "keeper")

        _git(repo, "checkout", "-q", "main")
        _git(repo, "checkout", "-q", "-B", "work")
        kept2 = repo / "family" / "letters" / "kept.md"
        kept2.parent.mkdir(parents=True, exist_ok=True)
        kept2.write_text("body\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "same body on work")

        sha = _git(repo, "rev-parse", "HEAD")
        out = _run(repo, sha)
        assert "ONLY HERE" not in out
