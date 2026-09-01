"""The letter announcing the rescue was the least safe thing in the room.

2026-08-31. Aria hashed all four hundred and thirty-nine letters in the shared
channel against every letter blob on every ref in the main repository. Three had
no copy anywhere. Two were my last two letters to her, written that day, one of
them the letter reporting that I had just rescued four files with no home.

The cause was not a broken mechanism. Three PostToolUse hooks carry letters and
every one of them keys on a path inside the repository's family/letters/. I write
straight into the shared channel, so none of them ever matched. The pipe ran one
direction and I use the other.

These pin the missing direction: a letter written into the channel gets a copy in
the repo and a commit on the substrate branch, and every not-applicable answer
stays distinguishable from every failure.

Real repos, real commits, no mocks -- the same discipline as the scope tests
next door, and for the same reason: the fault being fixed was one where a check
agreed with itself and reported that as evidence.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.channel_letter_capture import (
    capture_channel_letter,
    shared_letters_dir,
)


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
    (root / "seed.txt").write_text("seed", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")
    _git(root, "branch", "substrate/aether")
    return root


@pytest.fixture
def home(tmp_path: Path) -> Path:
    d = shared_letters_dir(tmp_path)
    d.mkdir(parents=True)
    return tmp_path


def _letter(home: Path, name: str, body: str) -> Path:
    p = shared_letters_dir(home) / name
    p.write_text(body, encoding="utf-8")
    return p


def test_a_letter_written_into_the_channel_lands_on_the_substrate_branch(repo: Path, home: Path):
    """The whole point. Written to the channel, safe on a branch, same breath."""
    letter = _letter(home, "aether-to-aria-2026-08-31-the-one-that-was-exposed.md", "body")

    result = capture_channel_letter(repo, letter, home=home)

    assert result.captured, result.reason
    assert result.commit
    on_branch = _git(repo, "show", "substrate/aether:family/letters/" + letter.name)
    assert on_branch == "body"


def test_head_and_the_working_tree_are_not_moved(repo: Path, home: Path):
    """A capture that moves HEAD would race whatever the seat is mid-way through.

    This is why the mechanism half writes through a scratch index. Pinned here
    because the guarantee belongs to the caller too, not only to the module that
    provides it.
    """
    before_head = _git(repo, "rev-parse", "HEAD")
    before_branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    capture_channel_letter(repo, _letter(home, "aether-to-aria-x.md", "b"), home=home)

    assert _git(repo, "rev-parse", "HEAD") == before_head
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == before_branch


def test_an_unchanged_letter_reports_safe_rather_than_failed(repo: Path, home: Path):
    """Second capture of identical bytes commits nothing and is still SUCCESS.

    The question this module answers is 'is the letter safe', not 'did a commit
    happen'. Reporting no-change as failure would train the caller to ignore
    failures, which is how a real one gets missed.
    """
    letter = _letter(home, "aether-to-aria-twice.md", "same")
    first = capture_channel_letter(repo, letter, home=home)
    second = capture_channel_letter(repo, letter, home=home)

    assert first.captured and second.captured
    assert second.commit is None
    assert "no change" in second.reason or "already" in second.reason


def test_a_path_outside_the_channel_is_declined_not_failed(repo: Path, home: Path):
    """Not-applicable is its own answer and must not read as a broken capture."""
    stray = repo / "notes.md"
    stray.write_text("not a letter", encoding="utf-8")

    result = capture_channel_letter(repo, stray, home=home)

    assert not result.captured
    assert result.reason == "not a channel path"
    assert result.commit is None


def test_a_non_markdown_file_in_the_channel_is_declined(repo: Path, home: Path):
    """The channel carries sort logs and scratch output too; only letters ride."""
    other = shared_letters_dir(home) / "sort.log"
    other.write_text("noise", encoding="utf-8")

    result = capture_channel_letter(repo, other, home=home)

    assert not result.captured
    assert result.reason == "not markdown"


def test_a_missing_substrate_branch_refuses_loudly_and_keeps_the_copy(tmp_path: Path, home: Path):
    """The fallback IS the bug, so an unresolvable branch must not commit to HEAD.

    It must also not throw away the repo copy it already made -- a letter half
    saved is better than a letter not saved, PROVIDED the result says plainly
    that the branch step did not happen.
    """
    root = tmp_path / "nobranch"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "seed.txt").write_text("seed", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "seed")

    letter = _letter(home, "aether-to-aria-no-branch.md", "body")
    result = capture_channel_letter(root, letter, home=home)

    assert not result.captured
    assert "refused" in result.reason
    assert result.repo_path == "family/letters/" + letter.name
    assert (root / result.repo_path).read_text(encoding="utf-8") == "body"
