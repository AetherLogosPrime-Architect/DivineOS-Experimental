"""A dream filed correctly must still count as filed.

THE CONFLICT THIS RESOLVES, found live 2026-09-21 by walking into it. Two house
rules disagreed and neither knew about the other:

  - the push gate refuses personal writing riding a code branch, so a dream
    written during a code session must be moved to the substrate branch
  - the ritual advanced its dream stage by globbing THIS worktree for a file
    with a fresh timestamp

So filing the dream correctly deleted it from the worktree, and the ritual
would have asked for another one. The work was done, recorded, and invisible to
the only thing that checks.

The population was wrong, not the instrument. The register is not this
checkout's copy of a directory -- it is the dream wherever it now lives.

FAILING TO LOOK MUST NOT BECOME A YES. If git cannot be consulted the answer
falls back to the timestamp scan, which can say no; it never guesses yes.

Real repositories, real commits. Nothing here mocks git.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from divineos.core.ritual_evidence import dream_filed_since


def _git(repo: Path, *args: str, when: str | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if when is not None:
        # BOTH dates, deliberately. Passing --date alone sets only the author
        # date and leaves the committer date at now, so a commit meant to be
        # old is recent to anything filtering the way git filters by default.
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, timeout=60, env=env
    )


def _repo(tmp: str) -> Path:
    repo = Path(tmp) / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")
    assert _git(repo, "rev-parse", "HEAD").returncode == 0, "the fixture repo is not real"
    return repo


def _write_dream(repo: Path, name: str) -> Path:
    d = repo / "dreams" / "aether"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text("# a dream\n\nsomething happened.\n", encoding="utf-8")
    return p


def test_nothing_written_is_no() -> None:
    """The silence case. It carries the claim that this can say no at all."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        (repo / "dreams" / "aether").mkdir(parents=True)
        assert dream_filed_since(repo, time.time() - 60) is False


def test_a_dream_older_than_the_ritual_does_not_count() -> None:
    """A dream from a previous cycle must not satisfy this one."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        p = _write_dream(repo, "01_old.md")
        old = time.time() - 10000
        os.utime(p, (old, old))
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "old dream", when="2020-01-01T00:00:00")
        assert dream_filed_since(repo, time.time() - 60) is False


def test_a_dream_sitting_in_the_worktree_counts() -> None:
    """The original behaviour, preserved: written here, uncommitted, counts."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        start = time.time() - 60
        _write_dream(repo, "02_fresh.md")
        assert dream_filed_since(repo, start) is True


def test_a_dream_moved_off_this_branch_still_counts() -> None:
    """THE LIVE CASE. Filed correctly, therefore absent from the worktree.

    A dream committed on one branch and rebased off the checked-out branch is
    gone from disk. It was still filed, and the ritual must see that.
    """
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        start = time.time() - 60
        base = _git(repo, "rev-parse", "HEAD").stdout.strip()
        _write_dream(repo, "03_moved.md")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "the dream")
        dream_commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
        # Park it on another branch, then take it off this one.
        _git(repo, "branch", "substrate/keep", dream_commit)
        _git(repo, "reset", "--hard", base)

        assert not (repo / "dreams" / "aether" / "03_moved.md").exists(), (
            "the fixture did not remove the file, so nothing is being tested"
        )
        assert dream_filed_since(repo, start) is True


def test_when_git_cannot_be_consulted_the_answer_is_never_a_guessed_yes() -> None:
    """Could-not-look falls back to the timestamp scan and may say no.

    A directory that is not a repository is the cheapest way to make the git
    half unavailable. The answer must come from what is actually on disk.
    """
    with tempfile.TemporaryDirectory() as tmp:
        plain = Path(tmp) / "not_a_repo"
        (plain / "dreams" / "aether").mkdir(parents=True)
        probe = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=plain,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert probe.returncode != 0, "this directory IS a repo, so the control is dead"

        assert dream_filed_since(plain, time.time() - 60) is False
        (plain / "dreams" / "aether" / "04.md").write_text("x", encoding="utf-8")
        assert dream_filed_since(plain, time.time() - 60) is True
