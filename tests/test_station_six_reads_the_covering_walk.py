"""Station 6 judges freshness by the covering walk's own close time.

Station 2 decides on a CLOSED walk scoped to the changed files. Station 6 used
to ask a different store (the newest lens event anywhere), so a branch whose
covering walk closed after its last commit still read "predates the last build"
(Aria, #619), and a branch whose files this seat never edited read "no walk"
(#599). These tests use a real git repository, so the commit time is git's.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from divineos.cli.build_flow_commands import _walk_postdates_build
from divineos.core.council_walk import Coverage

COMMIT_TIME = 1_800_000_000


def _git(repo: Path, *args: str, when: int | None = None) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t"}
    env |= {"GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    if when is not None:
        env["GIT_COMMITTER_DATE"] = f"{when} +0000"
        env["GIT_AUTHOR_DATE"] = f"{when} +0000"
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


@pytest.fixture
def branch_repo(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("a")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-q", "-m", "base", when=COMMIT_TIME - 1000)
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(tmp_path, "checkout", "-q", "-b", "work")
    (tmp_path / "b.txt").write_text("b")
    _git(tmp_path, "add", "b.txt")
    _git(tmp_path, "commit", "-q", "-m", "work", when=COMMIT_TIME)
    monkeypatch.chdir(tmp_path)
    return "work"


def _covered(closed_at):
    return Coverage("covered", walk_id="w", lenses=8, closed_at=closed_at)


def test_a_covering_walk_closed_after_the_last_commit_is_fresh(branch_repo):
    assert _walk_postdates_build(branch_repo, _covered(COMMIT_TIME + 3600)) is True


def test_a_covering_walk_closed_before_the_last_commit_is_stale(branch_repo):
    assert _walk_postdates_build(branch_repo, _covered(COMMIT_TIME - 3600)) is False


def test_a_walk_closed_in_the_same_second_as_the_last_commit_is_stale(branch_repo):
    assert _walk_postdates_build(branch_repo, _covered(COMMIT_TIME)) is False


def test_a_covering_walk_with_no_readable_close_time_cannot_be_checked(branch_repo):
    assert _walk_postdates_build(branch_repo, _covered(None)) is None


def test_a_partial_walk_does_not_decide_freshness(branch_repo):
    """Only a fully covered walk may pass. A partial one falls to the old reading
    of the ledger; COMMIT_TIME is in the future, so no real lens event postdates
    it and the answer is False even though the offered walk closed after it."""
    partial = Coverage("partial", walk_id="w", lenses=8, closed_at=COMMIT_TIME + 3600)
    assert _walk_postdates_build(branch_repo, partial) is False
