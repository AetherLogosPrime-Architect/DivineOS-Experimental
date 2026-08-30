"""Tests for committing substrate to a named branch without touching HEAD.

Real repositories throughout. The defect under repair is entirely about which
ref a commit lands on and what the working tree looks like afterwards, so a
mocked git would test the mock and nothing else.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.substrate_retarget import (
    RetargetRefused,
    commit_paths_to_branch,
)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    (r / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "seed.txt")
    _git(r, "commit", "-q", "-m", "seed")
    _git(r, "branch", "substrate")
    _git(r, "checkout", "-q", "-b", "work")
    return r


def test_commits_to_named_branch_not_head(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    head_before = _git(repo, "rev-parse", "HEAD")

    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == result.commit
    assert _git(repo, "rev-parse", "HEAD") == head_before, "HEAD must not move"
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "work"


def test_working_tree_and_index_are_untouched(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    (repo / "wip.py").write_text("x = 1\n", encoding="utf-8")

    commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    # Both files are still present and still untracked on the occupant's branch.
    assert (repo / "letter.md").read_text(encoding="utf-8") == "hello\n"
    assert (repo / "wip.py").read_text(encoding="utf-8") == "x = 1\n"
    porcelain = _git(repo, "status", "--porcelain")
    assert "?? wip.py" in porcelain
    assert _git(repo, "diff", "--cached", "--name-only") == "", "real index must stay clean"


def test_work_in_progress_does_not_ride_along(repo: Path) -> None:
    """The whole defect, from the other direction.

    Naming the substrate branch correctly still sends half-finished work there
    if the commit is built from `add -A`. Only the declared paths may travel.
    """
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    (repo / "half_finished.py").write_text("def broken(\n", encoding="utf-8")

    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    landed = _git(repo, "show", "--name-only", "--format=", result.commit).split()
    assert landed == ["letter.md"]


def test_missing_branch_refuses_and_commits_nothing(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    head_before = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(RetargetRefused, match="does not exist"):
        commit_paths_to_branch(repo, "no-such-branch", ["letter.md"], "m")

    assert _git(repo, "rev-parse", "HEAD") == head_before
    assert _git(repo, "status", "--porcelain") != "", "the file is still uncommitted"


def test_no_change_makes_no_commit(repo: Path) -> None:
    """An empty commit would make the log assert work that did not happen."""
    tip_before = _git(repo, "rev-parse", "refs/heads/substrate")

    assert commit_paths_to_branch(repo, "substrate", ["seed.txt"], "m") is None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == tip_before


def test_empty_path_list_is_a_noop(repo: Path) -> None:
    tip_before = _git(repo, "rev-parse", "refs/heads/substrate")
    assert commit_paths_to_branch(repo, "substrate", [], "m") is None
    assert _git(repo, "rev-parse", "refs/heads/substrate") == tip_before


def test_does_not_seed_from_head(repo: Path) -> None:
    """Seeding the scratch index from HEAD would carry the occupant's branch
    across onto substrate -- the same contamination pointed the other way."""
    (repo / "only_on_work.txt").write_text("work\n", encoding="utf-8")
    _git(repo, "add", "only_on_work.txt")
    _git(repo, "commit", "-q", "-m", "work-only commit")

    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    result = commit_paths_to_branch(repo, "substrate", ["letter.md"], "substrate: letter")

    assert result is not None
    files = _git(repo, "ls-tree", "-r", "--name-only", result.commit).split()
    assert "only_on_work.txt" not in files
    assert sorted(files) == ["letter.md", "seed.txt"]


def test_deleted_substrate_file_records_as_deleted(repo: Path) -> None:
    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    first = commit_paths_to_branch(repo, "substrate", ["letter.md"], "add")
    assert first is not None

    (repo / "letter.md").unlink()
    second = commit_paths_to_branch(repo, "substrate", ["letter.md"], "remove")

    assert second is not None
    files = _git(repo, "ls-tree", "-r", "--name-only", second.commit).split()
    assert "letter.md" not in files


def test_concurrent_branch_move_is_refused_not_clobbered(repo: Path) -> None:
    """The in-flight window, made explicit.

    If the substrate branch moves between our read and our write, the update
    must fail rather than discard whatever arrived.
    """
    from divineos.core import substrate_retarget as sr

    (repo / "letter.md").write_text("hello\n", encoding="utf-8")
    real_commit_tree = sr._git
    state = {"moved": False}

    def racing_git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
        out = real_commit_tree(root, *args, env=env)
        if args and args[0] == "commit-tree" and not state["moved"]:
            state["moved"] = True
            # Someone else advances substrate while we were building the tree.
            _git(repo, "branch", "-f", "substrate", "main")
            (repo / "other.txt").write_text("other\n", encoding="utf-8")
        return out

    sr._git = racing_git
    try:
        # substrate == main here, so force it somewhere else first to make the
        # move observable.
        _git(repo, "commit", "-q", "--allow-empty", "-m", "advance work")
        _git(repo, "branch", "-f", "substrate", "HEAD")
        with pytest.raises(RetargetRefused):
            commit_paths_to_branch(repo, "substrate", ["letter.md"], "m")
    finally:
        sr._git = real_commit_tree
