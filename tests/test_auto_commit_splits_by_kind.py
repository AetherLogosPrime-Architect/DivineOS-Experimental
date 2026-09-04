"""The checkpoint saves everything, and stops making someone take it apart.

On 2026-09-03 a checkpoint swept eighteen letters onto a branch carrying
nothing but an anchor fix. The push gate refused it, correctly, and the cure
was a manual three-branch rebuild -- in which the tempting shortcut, dropping
the checkpoint commits and trusting the reflog, risked the only copies of
those letters anywhere in the tree.

``substrate_paths.partition`` was written for this exact call on 2026-08-27 and
then never called: measured, its only importer was its own test, while a second
copy of the same logic grew inside a script. Built, correct, tested, unwired.

These drive the real function against a real repository. The contract pinned
here is narrow and it is the whole point:

  * nothing is excluded and nothing is refused -- the save-work contract that
    makes this safe to run unattended is untouched;
  * the tree still goes clean, so the next checkpoint does not find the same
    files again;
  * when both kinds are present they land in SEPARATE commits, work first, so
    a code branch that picked up letters is trimmed by dropping the tip.

The failure directions matter more than the happy path: every way the split can
fail must fall back to the single commit, because losing the split costs a
manual cleanup and losing the save costs the work itself.

Companion to ``test_auto_commit.py``, which covers the skip conditions and the
external-channel sync.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.auto_commit import auto_commit_substrate
from divineos.core.uncommitted_work_check import ExternalChannel


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture()
def repo(tmp_path):
    root = tmp_path / "repo"
    (root / "family" / "letters").mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "t@example.com", cwd=root)
    _git("config", "user.name", "t", cwd=root)
    (root / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "seed", cwd=root)
    return root


@pytest.fixture()
def channels(tmp_path):
    """One declared channel whose mirror is the letters directory.

    The source is empty on purpose: the sync copies nothing, so what is under
    test is the partition by mirror rather than the copy.
    """
    source = tmp_path / "shared"
    source.mkdir()
    return (
        ExternalChannel(
            name="letters",
            source=source,
            repo_mirror=Path("family/letters"),
            pattern="*.md",
        ),
    )


def _subjects(root: Path) -> list[str]:
    out = _git("log", "--format=%s", "main", cwd=root)
    return [line for line in out.splitlines() if line.strip()]


def _files_in(root: Path, rev: str) -> set[str]:
    out = _git("show", "--name-only", "--format=", rev, cwd=root)
    return {line.strip() for line in out.splitlines() if line.strip()}


def test_both_kinds_land_in_separate_commits_with_work_first(repo, channels):
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert result.committed is True
    subjects = _subjects(repo)
    assert len(subjects) == 3, f"expected two checkpoint commits over the seed: {subjects}"
    # git log is newest first, so substrate is [0] and work is [1].
    assert "substrate checkpoint" in subjects[0]
    assert "work in progress" in subjects[1]
    assert _files_in(repo, "HEAD") == {"family/letters/a.md"}
    assert _files_in(repo, "HEAD~1") == {"module.py"}


def test_the_tree_goes_clean_so_the_next_checkpoint_finds_nothing(repo, channels):
    """The save-work contract. A split leaving files behind is worse than none."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert _git("status", "--porcelain", cwd=repo) == "", (
        "the checkpoint left files uncommitted; the next one will find them again"
    )
    again = auto_commit_substrate(repo, reason="pre-sleep", channels=channels)
    assert again.committed is False


def test_nothing_is_dropped_when_both_kinds_are_present(repo, channels):
    """Everything staged lands in one of the two commits. No path may vanish."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "other.py").write_text("y = 2\n", encoding="utf-8")
    for n in ("a", "b", "c"):
        (repo / "family" / "letters" / f"{n}.md").write_text(n, encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    landed = _files_in(repo, "HEAD") | _files_in(repo, "HEAD~1")
    assert landed == {
        "module.py",
        "other.py",
        "family/letters/a.md",
        "family/letters/b.md",
        "family/letters/c.md",
    }


def test_substrate_only_stays_one_commit(repo, channels):
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert result.committed is True
    subjects = _subjects(repo)
    assert len(subjects) == 2
    assert "substrate checkpoint" in subjects[0]


def test_work_only_says_work_rather_than_calling_itself_substrate(repo, channels):
    """The old subject called every checkpoint a substrate one, including those
    carrying no substrate at all. A commit whose subject misnames its contents
    is what made the queue hard to read at a glance."""
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert "work in progress" in _subjects(repo)[0]


def test_a_broken_channel_config_still_saves_the_work(repo):
    """A broken configuration must not cost the save.

    ``partition`` raises rather than classifying everything as work when no
    channel is declared -- correctly, because those two are indistinguishable
    at the call site. The checkpoint has to catch that and commit anyway.
    """
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "family" / "letters" / "a.md").write_text("dear\n", encoding="utf-8")

    result = auto_commit_substrate(repo, reason="pre-extract", channels=())

    assert result.committed is True, "a broken channel config swallowed the work"
    assert _git("status", "--porcelain", cwd=repo) == ""
    assert _files_in(repo, "HEAD") == {"module.py", "family/letters/a.md"}


def test_a_deleted_substrate_file_is_still_split_correctly(repo, channels):
    """Deletions are staged too, and a pathspec reset has to carry them.

    Written because the split unstages by pathspec and then restages by
    pathspec, and a deletion is the case where those two operations are least
    alike -- `git add` on a removed path has to be told the path still counts.
    """
    letter = repo / "family" / "letters" / "old.md"
    letter.write_text("old\n", encoding="utf-8")
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "letter", cwd=repo)

    letter.unlink()
    (repo / "module.py").write_text("x = 1\n", encoding="utf-8")

    auto_commit_substrate(repo, reason="pre-extract", channels=channels)

    assert _git("status", "--porcelain", cwd=repo) == "", (
        "the deletion was not carried through the split and is still pending"
    )
    landed = _files_in(repo, "HEAD") | _files_in(repo, "HEAD~1")
    assert landed == {"module.py", "family/letters/old.md"}
