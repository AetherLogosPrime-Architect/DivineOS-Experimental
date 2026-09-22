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
def repo(tmp_path, monkeypatch):
    """A real repo with a substrate branch, a feature branch, and a channel.

    THE CHANNEL IS DECLARED HERE, and it has to be said out loud. This branch
    added a valve: the external-channel sync runs only when the branch is
    DECLARED for substrate, because the undeclared case was importing the whole
    correspondence onto whatever code branch happened to be checked out. These
    tests ask what the RETARGET does once files have arrived, so they declare
    the channel and go on asking their own question.

    Its sibling test_auto_commit.py was updated for the valve on the same
    branch and this file was not, so it went red on CI while passing on any
    machine where the flag happened to already be set -- tests asserting a
    promise the code had stopped making, with the environment deciding which
    answer you got. The valve itself is exercised below, where it is the
    subject rather than the weather.
    """
    monkeypatch.setenv("DIVINEOS_SUBSTRATE_BRANCH", "1")
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


class TestTheAnchorRuleReachesTheRetarget:
    """A letter quoting its own branch and a hash must not ride out.

    Aria found this and left it deliberately (2026-09-01). The existing unstage
    guard reads the INDEX, and this flow never fills it -- the retarget writes
    through a scratch index and the work-in-progress commit has already emptied
    the real one. So the guard runs, finds nothing, and reports clean:
    could-not-see wearing the clothes of nothing-there.

    She would not guess the repair inside her own merge and named it as
    belonging with the seat that wrote the anchor rule. That is me, so the reach
    into the retarget's own path list is mine.

    Dropped rather than refused, matching what the unstage did and for her
    reason: this module's contract is to save work, not block a checkpoint. The
    letter stays on disk and in the shared channel, which is where the crossing
    actually happens. Only the archive copy waits, and it waits one checkpoint.
    """

    def _anchored_letter(self, channels, branch: str) -> None:
        (channels[0].source / "aria-to-aether-anchored.md").write_text(
            f"I pushed to {branch}, and its tip is 1a2b3c4d5e6f7890 as I write this.\n",
            encoding="utf-8",
        )

    def test_the_anchored_letter_does_not_reach_the_substrate_branch(self, repo):
        r, channels = repo
        self._anchored_letter(channels, "substrate")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        on_substrate = _git(r, "ls-tree", "-r", "--name-only", "substrate")
        assert "aria-to-aether-anchored.md" not in on_substrate, (
            "a letter quoting the substrate tip rode out in the commit that falsified it"
        )

    def test_the_ordinary_letters_beside_it_still_land(self, repo):
        """Holding one file back must not hold the batch back."""
        r, channels = repo
        self._anchored_letter(channels, "substrate")

        result = auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert result.committed, result.reason
        assert "family/letters/aria-to-aether-note.md" in _git(
            r, "ls-tree", "-r", "--name-only", "substrate"
        )

    def test_the_held_letter_is_still_on_disk(self, repo):
        """Dropped from the commit, not deleted."""
        r, channels = repo
        self._anchored_letter(channels, "substrate")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert (r / "family/letters/aria-to-aether-anchored.md").exists()

    def test_an_anchor_naming_a_different_branch_is_not_held(self, repo):
        """The rule is self-invalidation, not the presence of a hash. A letter
        quoting some other branch's tip stays true after this commit, and
        holding it anyway would make the guard a hash-detector -- which is the
        name-for-identity fault the rest of this week was made of."""
        r, channels = repo
        self._anchored_letter(channels, "some-other-branch")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert "aria-to-aether-anchored.md" in _git(r, "ls-tree", "-r", "--name-only", "substrate")


class TestTheValveIsItsOwnSubject:
    """The gate the fixture declares past, tested where it belongs.

    Every other test in this file sets the declaration and then asks a question
    about the retarget. That is right for those tests, and it means none of
    them can see the valve -- which is exactly how this file went red on CI
    while green on a machine that happened to carry the flag. A condition every
    test satisfies is a condition no test measures.
    """

    def test_an_undeclared_branch_does_not_import_the_correspondence(self, repo, monkeypatch):
        """The defect the valve was built for: a letter written in the shared
        room coming home to whatever code branch was checked out, and the push
        gate then refusing the branch. Three times in two days, growing each
        time, because an unvisited branch shows an empty mirror and the sweep
        becomes the whole correspondence rather than the day's."""
        r, channels = repo
        monkeypatch.delenv("DIVINEOS_SUBSTRATE_BRANCH", raising=False)

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        # THE ASSERTION IS AGAINST THE BRANCH, NOT THE DISK, and the first
        # draft of this test got that wrong. Asking whether the file is on
        # disk cannot separate "never imported" from "imported, committed and
        # then evicted" -- both leave the working tree without it. The test
        # passed with the valve forced permanently open, and only a mutation
        # probe said so. The same two-outputs-for-three-situations fault this
        # whole day has been about, committed inside the test written to
        # prevent it.
        assert "family/letters/aria-to-aether-note.md" not in _git(
            r, "ls-tree", "-r", "--name-only", "substrate"
        ), "the letter was imported from a branch nobody declared for substrate"

    def test_the_letter_is_still_where_it_was_written(self, repo, monkeypatch):
        """Not imported is not lost, and that difference is the whole argument
        for the valve. The shared room is where both seats read from, so
        refusing to make a second copy on a code branch takes nothing away."""
        r, channels = repo
        monkeypatch.delenv("DIVINEOS_SUBSTRATE_BRANCH", raising=False)

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert (channels[0].source / "aria-to-aether-note.md").exists()

    def test_work_in_progress_is_still_saved_on_an_undeclared_branch(self, repo, monkeypatch):
        """The valve must not cost the occupant their unfinished work. A
        configuration gap becoming data loss is the failure this whole module
        was written against, and it is the one easiest to reintroduce by
        putting a guard one line too early."""
        r, channels = repo
        monkeypatch.delenv("DIVINEOS_SUBSTRATE_BRANCH", raising=False)
        (r / "half_done.py").write_text("wip\n", encoding="utf-8")

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert "half_done.py" in _git(r, "ls-tree", "-r", "--name-only", "feature")

    def test_declaring_it_does_import(self, repo):
        """The control in the other direction. Without it a valve stuck
        permanently shut would pass all three tests above."""
        r, channels = repo

        auto_commit_substrate(r, reason="pre-extract", channels=channels)

        assert "family/letters/aria-to-aether-note.md" in _git(
            r, "ls-tree", "-r", "--name-only", "substrate"
        )
