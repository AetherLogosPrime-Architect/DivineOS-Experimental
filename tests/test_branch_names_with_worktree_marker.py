"""A branch open in another worktree must not read as a different branch.

2026-10-07, claim run. reach_check says abandoned `dead/` branches are left out of
the commit-subject search. Run against a real repository it held only while nobody
had the branch open: git writes "+ " before a branch checked out in another
worktree, the code stripped only "*", so "+ dead/x" failed the prefix test, was
listed as live, and was printed with the plus inside its name. This project works
in worktrees all the time. The same expression sat in prior_art. These tests build
a real repository and a real worktree; a mock of git output would have agreed with
whatever the code assumed.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core import prior_art, reach_check


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert done.returncode == 0, (args, done.stderr)
    return done.stdout.strip()


def _commit_on_branch(repo: Path, base: str, name: str, subject: str) -> None:
    _git(repo, "checkout", "-q", "-b", name, base)
    (repo / f"freeze_{name.replace('/', '_')}.txt").write_text(name, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", subject)
    _git(repo, "checkout", "-q", "main")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "r"
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.email", "t@t")
    _git(path, "config", "user.name", "t")
    (path / "a.txt").write_text("a", encoding="utf-8")
    _git(path, "add", ".")
    _git(path, "commit", "-q", "-m", "base")
    base = _git(path, "rev-parse", "HEAD")
    _git(path, "update-ref", "refs/remotes/origin/main", base)
    _commit_on_branch(path, base, "dead/old", "freeze fix attempt one")
    _commit_on_branch(path, base, "live/new", "freeze fix attempt two")
    monkeypatch.setattr(prior_art, "REPO", path)
    return path


def _branches(found) -> list[str]:
    return [branch for _subject, _sha, branch in found]


def test_control_a_dead_branch_nobody_has_open_is_left_out(repo: Path) -> None:
    assert _branches(reach_check.find_in_commit_subjects("freeze")) == ["live/new"]


def test_a_dead_branch_open_in_another_worktree_is_still_left_out(
    repo: Path, tmp_path: Path
) -> None:
    _git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "dead/old")
    assert _branches(reach_check.find_in_commit_subjects("freeze")) == ["live/new"]


def test_a_live_branch_open_in_another_worktree_is_listed_without_the_marker(
    repo: Path, tmp_path: Path
) -> None:
    _git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "live/new")
    names = _branches(reach_check.find_in_commit_subjects("freeze"))
    assert names == ["live/new"]


def test_prior_art_names_a_worktree_branch_without_the_marker(repo: Path, tmp_path: Path) -> None:
    _git(repo, "worktree", "add", "-q", str(tmp_path / "wt"), "live/new")
    names = [branch for _line, _sha, branch in prior_art.find_elsewhere_in_git("freeze", set())]
    assert names, "the control found nothing, so the assertion below would be vacuous"
    assert all(not name.startswith(("+", "*", " ")) for name in names), names
