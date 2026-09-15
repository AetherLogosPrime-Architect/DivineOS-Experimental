"""The checkpoint swept hundreds of letters onto code branches, every time.

2026-09-15, after it happened three times in one session, twice mid-push on the
branch being cleaned. Andrew: "what is going on with the hundreds of letters
being dumped every time? that needs deeply investigated... this bug dies today."

THE MECHANISM. The channel sync compared the shared letters directory against
``mirror.glob()`` -- the CURRENT BRANCH's working tree. On the branch that keeps
writing that tree already holds every letter, so nothing copied. On a code
branch it holds almost none, so every letter read as missing, got copied in,
and ``git add -A`` staged them for the checkpoint commit.

PREDICTED BEFORE REPRODUCED, which is what makes it a cause rather than a story
that fits: computing the gap between the shared channel and each branch's
tracked set said 246 letters for main and for every code branch, and 0 for the
writing branch. The sweep that had just landed carried 246.

THE CONFUSION IN ONE LINE: missing from this branch is not missing from the
repository. The rescue is real -- a letter living only in the shared directory
is one disk failure from gone -- but a letter already on the writing branch is
safe, and copying it onto a code branch rescues nothing while contaminating a
branch whose one claim is that it carries no writing. Measured at fix time: of
the whole channel, the number genuinely at risk was ZERO.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import _names_anywhere_in_history, _sync_external_channels
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture
def repo_and_channel(tmp_path: Path) -> tuple[Path, Path, ExternalChannel]:
    """A repo with letters committed on a writing branch, plus a bare code branch."""
    repo = tmp_path / "repo"
    (repo / "family" / "letters").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@e.com")
    _git(repo, "config", "user.name", "t")

    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")

    # The writing branch carries the letters.
    _git(repo, "checkout", "-qb", "writing")
    for name in ("a.md", "b.md", "c.md"):
        (repo / "family" / "letters" / name).write_text(f"letter {name}\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "letters")

    # A code branch off base, which therefore carries none of them.
    _git(repo, "checkout", "-q", "master")
    _git(repo, "checkout", "-qb", "code")

    shared = tmp_path / "shared"
    shared.mkdir()
    for name in ("a.md", "b.md", "c.md"):
        (shared / name).write_text(f"letter {name}\n", encoding="utf-8")

    channel = ExternalChannel(
        name="letters",
        source=shared,
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    )
    return repo, shared, channel


def test_the_live_shape_copies_nothing_onto_a_code_branch(repo_and_channel) -> None:
    """THE BUG. Three letters, none on this branch, all safe on the writing one."""
    repo, _shared, channel = repo_and_channel
    assert not list((repo / "family" / "letters").glob("*.md")), "code branch starts bare"

    copied = _sync_external_channels((channel,), repo)

    assert copied == 0
    assert not list((repo / "family" / "letters").glob("*.md")), (
        "a letter already committed on the writing branch must not be copied onto a "
        "code branch -- that rescues nothing and contaminates the branch"
    )


def test_a_letter_that_exists_nowhere_is_still_rescued(repo_and_channel) -> None:
    """The rescue is REAL and must survive the fix, or the repair breaks the
    thing the function exists for."""
    repo, shared, channel = repo_and_channel
    (shared / "brand-new.md").write_text("only in the channel\n", encoding="utf-8")

    copied = _sync_external_channels((channel,), repo)

    assert copied == 1
    assert (repo / "family" / "letters" / "brand-new.md").is_file()
    assert not (repo / "family" / "letters" / "a.md").exists(), "the safe ones stayed put"


def test_the_writing_branch_still_gets_its_own_new_letters(repo_and_channel) -> None:
    repo, shared, channel = repo_and_channel
    _git(repo, "checkout", "-q", "writing")
    (shared / "fresh.md").write_text("written this session\n", encoding="utf-8")

    assert _sync_external_channels((channel,), repo) == 1
    assert (repo / "family" / "letters" / "fresh.md").is_file()


def test_history_reports_every_name_any_ref_has_held(repo_and_channel) -> None:
    repo, _shared, _channel = repo_and_channel
    ever = _names_anywhere_in_history(repo, "family/letters")
    assert ever == {"a.md", "b.md", "c.md"}, (
        "the walk must see the writing branch from the code branch -- that is the "
        "entire distinction the fix rests on"
    )


def test_an_unreadable_history_copies_nothing(tmp_path: Path) -> None:
    """A history walk that FAILS is not an empty history. Treating it as one
    would restore the sweep in its worst form -- every file reading as at-risk."""
    not_a_repo = tmp_path / "bare"
    (not_a_repo / "family" / "letters").mkdir(parents=True)
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "x.md").write_text("content\n", encoding="utf-8")

    assert _names_anywhere_in_history(not_a_repo, "family/letters") is None

    channel = ExternalChannel(
        name="letters", source=shared, repo_mirror=Path("family/letters"), pattern="*.md"
    )
    assert _sync_external_channels((channel,), not_a_repo) == 0
    assert not (not_a_repo / "family" / "letters" / "x.md").exists()


def test_a_missing_source_directory_is_not_an_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    channel = ExternalChannel(
        name="gone",
        source=tmp_path / "does-not-exist",
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    )
    assert _sync_external_channels((channel,), repo) == 0


# --- the prevention half: substrate goes to its own branch -----------------
#
# Aletheia named this gap the same day the detection half shipped: a scope
# station reports the mixture on every READ and does nothing about the WRITE.
# Her evidence was the cleanest available -- I removed one letter by hand from
# the branch whose whole purpose is refusing that mixture, and a checkpoint put
# hundreds back two minutes later, while I was writing to her about the fix.


def _staged(repo: Path) -> str:
    return subprocess.run(
        ["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True
    ).stdout


def _rev(repo: Path, what: str) -> str:
    return subprocess.run(
        ["git", "rev-parse", what], cwd=repo, capture_output=True, text=True
    ).stdout.strip()


def _repo_with_writing_branch(tmp_path: Path, name: str) -> Path:
    repo = tmp_path / name
    (repo / "family" / "letters").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@e.com")
    _git(repo, "config", "user.name", "t")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    _git(repo, "branch", "substrate/aether")
    _git(repo, "checkout", "-qb", "codework")
    return repo


def test_a_letter_staged_on_a_code_branch_goes_to_the_writing_branch(tmp_path: Path) -> None:
    """THE PREVENTION. It lands where writing belongs, not on the branch I stand on."""
    from divineos.core.auto_commit import _retarget_staged_substrate

    repo = _repo_with_writing_branch(tmp_path, "prevent")
    (repo / "family" / "letters" / "new.md").write_text("written now\n", encoding="utf-8")
    _git(repo, "add", "-A")

    _retarget_staged_substrate(repo)

    landed = subprocess.run(
        ["git", "cat-file", "-e", "substrate/aether:family/letters/new.md"],
        cwd=repo,
        capture_output=True,
    )
    assert landed.returncode == 0, "the letter must be committed on the writing branch"
    assert "family/letters" not in _staged(repo), "and must not stay staged for this branch"


def test_head_is_untouched_by_the_retarget(tmp_path: Path) -> None:
    """Switching branches to commit would open a window for a push already in
    flight to see a tree it did not expect -- the race that made this mess."""
    from divineos.core.auto_commit import _retarget_staged_substrate

    repo = _repo_with_writing_branch(tmp_path, "notouch")
    before, branch_before = _rev(repo, "HEAD"), _rev(repo, "--abbrev-ref")

    (repo / "family" / "letters" / "x.md").write_text("body\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _retarget_staged_substrate(repo)

    assert _rev(repo, "HEAD") == before
    assert _rev(repo, "--abbrev-ref") == branch_before


def test_code_is_left_alone(tmp_path: Path) -> None:
    from divineos.core.auto_commit import _retarget_staged_substrate

    repo = _repo_with_writing_branch(tmp_path, "codeonly")
    (repo / "mod.py").write_text("y = 2\n", encoding="utf-8")
    _git(repo, "add", "-A")

    _retarget_staged_substrate(repo)

    assert "mod.py" in _staged(repo), "code stays staged for this branch's own commit"


def test_no_writing_branch_leaves_the_old_behaviour_alone(tmp_path: Path) -> None:
    """A repo with no writing home has no contamination question, only a save
    question -- and the existing split already answers that. Declining to apply
    an improvement with nowhere to put its output is not the forbidden fallback."""
    from divineos.core.auto_commit import _retarget_staged_substrate

    repo = tmp_path / "nohome"
    (repo / "family" / "letters").mkdir(parents=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@e.com")
    _git(repo, "config", "user.name", "t")
    (repo / "code.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")
    _git(repo, "add", "-A")

    _retarget_staged_substrate(repo)

    assert "family/letters/a.md" in _staged(repo), "left staged so the existing split saves it"
