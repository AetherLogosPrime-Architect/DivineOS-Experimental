"""The completion probe says nothing, and says so, on a shallow checkout.

GitHub's test jobs check out at depth 1 (`actions/checkout@v4`, no fetch-depth). In a depth-1 clone the
only commit has no parent, so `git log --diff-filter=A` lists EVERY file as added by it. Aether measured
928 files against 4 on the public repo, and the slow completion-check test stalled in a `git grep` over
that many stems (it failed on 07-07 and 09-01 too). "Added in the last day" cannot be answered without
history, so the probe returns nothing and says so. walk-45fc51c7e6c5.

These build REAL repositories: a full one and a depth-1 clone of it, never a mocked git.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.core.completion_check import _is_shallow, _recently_added_files

MECHANISM = "src/divineos/core/a_new_mechanism.py"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)


@pytest.fixture
def full(tmp_path: Path) -> Path:
    """A real repo with an older commit and a recent one that added exactly one mechanism file."""
    repo = tmp_path / "full"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("old", encoding="utf-8")
    old = "2020-01-01T00:00:00"
    _git(repo, "add", "-A")
    subprocess.run(
        ["git", "commit", "-q", "-m", "old", "--date", old],
        cwd=repo,
        check=True,
        env={**__import__("os").environ, "GIT_COMMITTER_DATE": old},
    )
    (repo / "src" / "divineos" / "core").mkdir(parents=True)
    (repo / MECHANISM).write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "new mechanism")
    return repo


@pytest.fixture
def shallow(full: Path, tmp_path: Path) -> Path:
    """A depth-1 clone of the same repo, the shape GitHub's runner gets."""
    clone = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", full.as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    return clone


def test_a_full_history_checkout_names_the_one_file_added_today(full: Path) -> None:
    assert _recently_added_files(1, full) == [MECHANISM]


def test_a_depth_one_checkout_says_nothing_instead_of_every_file(shallow: Path) -> None:
    """Without the fix this returns the mechanism file AND every other tracked .py or .sh under the
    mechanism folders; here the repo is tiny, so the proof that matters is the empty list."""
    assert _recently_added_files(1, shallow) == []


def test_a_depth_one_checkout_says_so_aloud(
    shallow: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """[] reads as 'nothing unfinished', so quiet must never pass for clean (Godel)."""
    _recently_added_files(1, shallow)
    err = capsys.readouterr().err.lower()
    assert "shallow" in err and "not probed" in err


def test_a_full_checkout_prints_nothing_about_being_shallow(
    full: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _recently_added_files(1, full)
    assert "shallow" not in capsys.readouterr().err.lower()


def test_the_shallow_question_is_its_own_small_function(full: Path, shallow: Path) -> None:
    assert _is_shallow(full) is False
    assert _is_shallow(shallow) is True


def test_a_depth_two_checkout_is_still_shallow_and_quiet(full: Path, tmp_path: Path) -> None:
    """Conservative: a clone cut at any depth cannot say what was added in a window, so it says nothing."""
    clone = tmp_path / "depth2"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "2", full.as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    assert _is_shallow(clone) is True
    assert _recently_added_files(1, clone) == []


def test_a_folder_that_is_not_a_repo_still_gives_nothing() -> None:
    """A system temp folder, not pytest's tmp_path: this suite's base temp folder sits INSIDE this repo
    (the first run of this test returned this repo's own files), so tmp_path is not 'not a repo' here."""
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        assert _recently_added_files(7, Path(folder)) == []
        assert _is_shallow(Path(folder)) is False, "git cannot be asked, so the old behaviour stays"
