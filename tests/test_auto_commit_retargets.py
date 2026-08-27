"""The sweep, wired end to end, against real repositories.

Aria + Aether 2026-08-27. Seven times in one evening the checkpoint
committed the whole dirty tree onto whatever branch was checked out --
twice onto proposals already open for review. These build that exact
situation and assert it cannot recur.

The load-bearing one is `test_the_seventh_instance_cannot_recur`: a
feature branch checked out, half-finished work on it, a letter newly
synced, checkpoint fires. Before this wiring that produced one commit on
the feature branch carrying both.

Complements tests/test_auto_commit.py, which holds the older contract --
that a checkpoint never loses the occupant's unfinished work. Both
promises have to survive together, and the first draft of this change
kept one by dropping the other until six of those tests said so.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import auto_commit_substrate
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A real repo with a substrate branch, a feature branch, and a channel."""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    (r / "README.md").write_text("seed\n", encoding="utf-8")
    _git(r, "add", "README.md")
    _git(r, "commit", "-m", "seed")

    _git(r, "branch", "substrate")
    _git(r, "config", "divineos.substrate-branch", "substrate")
    _git(r, "checkout", "-b", "feature")

    source = tmp_path / "shared" / "letters"
    source.mkdir(parents=True)
    (source / "aria-to-aether-note.md").write_text("a letter\n", encoding="utf-8")

    channels = (
        ExternalChannel(
            name="letters",
            source=source,
            repo_mirror=Path("family/letters"),
            pattern="*.md",
        ),
    )
    return r, channels


class TestTheDefect:
    def test_the_seventh_instance_cannot_recur(self, repo):
        r, channels = repo
        # Half-finished work on the feature branch, exactly as it was.
        (r / "half_done.py").write_text("def broken(:\n", encoding="utf-8")

        result = auto_commit_substrate(r, reason="pre-extract", channels=channels)
        assert result.committed, result.reason

        on_substrate = _git(r, "ls-tree", "-r", "--name-only", "substrate")
        assert "family/letters/aria-to-aether-note.md" in on_substrate
        assert "half_done.py" not in on_substrate, (
            "work in progress rode along to substrate -- the same defect, pointed the other way"
        )

    def test_the_feature_branch_never_sees_the_letter(self, repo):
        r, channels = repo
        auto_commit_substrate(r, reason="pre-extract", channels=channels)
        assert "family/letters" not in _git(r, "ls-tree", "-r", "--name-only", "feature")

    def test_head_stays_on_the_branch_the_occupant_chose(self, repo):
        r, channels = repo
        auto_commit_substrate(r, reason="pre-extract", channels=channels)
        assert _git(r, "rev-parse", "--abbrev-ref", "HEAD") == "feature"


class TestBothPromisesTogether:
    """Substrate reaches its branch AND unfinished work is not lost."""

    def test_work_in_progress_is_still_saved(self, repo):
        r, channels = repo
        (r / "half_done.py").write_text("wip\n", encoding="utf-8")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert "half_done.py" in _git(r, "ls-tree", "-r", "--name-only", "feature")

    def test_the_two_commits_are_separate(self, repo):
        r, channels = repo
        (r / "half_done.py").write_text("wip\n", encoding="utf-8")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        feature_msg = _git(r, "log", "-1", "--format=%s", "feature")
        substrate_msg = _git(r, "log", "-1", "--format=%s", "substrate")
        assert "work in progress" in feature_msg
        assert "substrate checkpoint" in substrate_msg


class TestRefusal:
    def test_undeclared_branch_refuses_substrate_but_still_saves_work(self, repo):
        # A configuration gap must not become data loss. This ordering was
        # wrong in the first draft and six existing tests caught it.
        r, channels = repo
        _git(r, "config", "--unset", "divineos.substrate-branch")
        (r / "half_done.py").write_text("wip\n", encoding="utf-8")
        substrate_before = _git(r, "rev-parse", "substrate")

        result = auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert "substrate-branch" in result.reason
        assert _git(r, "rev-parse", "substrate") == substrate_before
        assert "half_done.py" in _git(r, "ls-tree", "-r", "--name-only", "feature")

    def test_declared_branch_that_does_not_exist_refuses(self, repo):
        r, channels = repo
        _git(r, "config", "divineos.substrate-branch", "no-such-branch")
        substrate_before = _git(r, "rev-parse", "substrate")
        auto_commit_substrate(r, reason="pre-extract", channels=channels)
        assert _git(r, "rev-parse", "substrate") == substrate_before


class TestPathReading:
    def test_a_letter_with_spaces_in_its_name_still_classifies(self, repo):
        # git quotes such names in its human-readable output; the reader
        # uses the NUL-separated form so nothing needs unquoting. A parser
        # splitting on whitespace would drop this file silently -- and
        # silently is how every fault tonight survived.
        r, channels = repo
        (channels[0].source / "a letter with spaces.md").write_text("x\n", encoding="utf-8")
        result = auto_commit_substrate(r, reason="pre-extract", channels=channels)
        assert result.committed, result.reason
        assert "a letter with spaces.md" in _git(r, "ls-tree", "-r", "--name-only", "substrate")
