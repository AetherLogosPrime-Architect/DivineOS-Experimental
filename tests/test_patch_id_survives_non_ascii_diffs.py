"""The patch-id computation must not die on a diff containing my own prose.

Aletheia computed a patch-id for a branch that returned nothing on my machine
and asked why, 2026-08-29. Reproduced: the diff was being read through the
locale text codec, which here is cp1252, and the branch's diff carried a byte
cp1252 cannot map. An em-dash or a curly quote is enough -- so nearly every
branch I own, because my comments and letters are full of them.

WORSE THAN A CRASH, AND THAT IS THE POINT OF THIS FILE. The decode error is a
ValueError, which the function's guard did not name, so it escaped to a broad
handler upstream and became a silent None. And a None there is
indistinguishable from "this branch has no diff to compare" -- so the
catch-up rung was permanently unavailable to those branches and nothing
anywhere said so. Her line: it should distinguish no-patch-id-because-the-
computation-failed from no-patch-id-because-there-is-nothing-to-compare.

Nothing tested this function before today. It is the anchor the whole
re-audit ladder rests on: without it, a review dies on the next commit and
cannot be carried forward, which is the treadmill the rung exists to end.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.cli.audit_commands import compute_branch_patch_id


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


def _commit(repo: Path, relative: str, text: str, message: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written as UTF-8 bytes explicitly: the whole subject of this file is what
    # happens when bytes meet the wrong codec, so the fixture must not itself
    # go through a locale-dependent write.
    path.write_bytes(text.encode("utf-8"))
    _git(repo, "add", "-A")
    _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)


@pytest.fixture
def repo_with_non_ascii_diff(tmp_path: Path) -> Path:
    """A repo whose branch diff carries the exact characters that broke it.

    Em-dash, curly quotes, and an ellipsis -- the punctuation my own writing
    uses constantly, and the reason this defect covered nearly every branch I
    own rather than some exotic edge.
    """
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _commit(root, "seed.txt", "plain ascii\n", "seed")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))

    _git(root, "checkout", "-q", "-b", "feature")
    _commit(
        root,
        "prose.md",
        "A line with an em-dash — and “curly quotes” and an ellipsis…\n",
        "prose the locale codec cannot read",
    )
    return root


def test_a_diff_full_of_my_own_punctuation_still_yields_a_patch_id(
    repo_with_non_ascii_diff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """THE ONE THAT MATTERS. Before the fix this returned None.

    Not a crash the caller could see -- a None that reads exactly like "this
    branch has nothing to compare", which is why it went unnoticed until
    someone on another machine computed the value and asked why mine was
    empty.
    """
    monkeypatch.chdir(repo_with_non_ascii_diff)
    result = compute_branch_patch_id("feature", "origin/main")
    assert result is not None, "non-ascii prose in a diff must not erase the anchor"
    assert len(result) == 40
    assert all(c in "0123456789abcdef" for c in result)


def test_it_matches_what_git_itself_reports(
    repo_with_non_ascii_diff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Computed independently through the shell, the way Aletheia did it.

    A value that is merely non-empty proves the crash is gone and nothing
    about correctness. This pins the value against git's own answer, which is
    the check that caught the bug in the first place -- her number and mine
    agreeing across two machines.
    """
    monkeypatch.chdir(repo_with_non_ascii_diff)
    base = _git(repo_with_non_ascii_diff, "merge-base", "origin/main", "feature")
    diff = subprocess.run(
        ["git", "diff", base, "feature"],
        cwd=str(repo_with_non_ascii_diff),
        capture_output=True,
        check=True,
    )
    expected = (
        subprocess.run(
            ["git", "patch-id", "--stable"],
            input=diff.stdout,
            cwd=str(repo_with_non_ascii_diff),
            capture_output=True,
            check=True,
        )
        .stdout.decode("ascii")
        .split()[0]
    )

    assert compute_branch_patch_id("feature", "origin/main") == expected


def test_an_unresolvable_branch_still_returns_none(
    repo_with_non_ascii_diff: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The genuine no-answer case must survive the repair.

    There are two reasons this function can return nothing and only one of
    them was a bug. Removing the bug must not remove the honest None, or the
    caller loses the ability to say "there is nothing here to compare".
    """
    monkeypatch.chdir(repo_with_non_ascii_diff)
    assert compute_branch_patch_id("no/such/branch", "origin/main") is None


def test_an_ascii_only_diff_was_never_affected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Guard the guard: plain diffs worked before and must still work.

    Without this, the fixture above could pass against a function that
    returns a constant, and the file would prove nothing about the general
    case.
    """
    root = tmp_path / "ascii"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    _commit(root, "seed.txt", "seed\n", "seed")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    _git(root, "checkout", "-q", "-b", "feature")
    _commit(root, "plain.txt", "nothing but ascii here\n", "plain")

    monkeypatch.chdir(root)
    result = compute_branch_patch_id("feature", "origin/main")
    assert result is not None
    assert len(result) == 40
