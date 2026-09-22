"""The surface that names personal writing left unsaved after a commit went past it.

THE SILENCE CASE IS WRITTEN FIRST AND IT IS THE ONE THAT CARRIES THE CLAIM.
A hook that shouts on every untracked file passes the noisy half trivially and
is worthless, because a line that prints while I am still writing becomes
furniture within a day. So the first test asserts that a freshly-written,
uncommitted piece produces nothing at all.

Real repositories, real commits, real timestamps. Nothing here mocks git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "unsaved-personal-writing-must-not-close-quiet.sh"
)


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

    Asking for bash by name on this box can return the WSL relay, which exists,
    runs, and cannot execute a Windows-path script. It fails by printing to
    stderr, which the silence tests below would have read as silence -- the
    hook never ran and three of them passed. That is the exact collapse this
    hook exists to prevent, committed inside the hook's own test file.
    """
    candidates = []
    git = shutil.which("git")
    if git:
        candidates.append(str(Path(git).with_name("bash.exe")))
        candidates.append(str(Path(git).parents[1] / "bin" / "bash.exe"))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()


def _bash() -> str:
    """A control that cannot be built must FAIL rather than skip.

    Three of the assertions below are absence assertions. If the hook cannot be
    run at all they pass trivially, and a skip would leave the whole file
    reporting green while testing nothing.
    """
    assert BASH is not None, (
        "no bash on this machine can run a Windows-path script, so this hook "
        "cannot be exercised. That is untested, not passing."
    )
    return BASH


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _new_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "dreams").mkdir()
    (repo / "exploration").mkdir()
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")
    return repo


def _run_hook(repo: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [_bash(), str(HOOK)],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    # The interpreter failing to start writes to the same channel the hook uses
    # to speak. Without this, "could not run" and "had nothing to say" arrive
    # as the same empty-looking result.
    assert "execvpe" not in result.stderr and "CreateProcessCommon" not in result.stderr, (
        f"the interpreter never ran the hook:\n{result.stderr}"
    )
    return result


def _age(path: Path, seconds: int) -> None:
    """Push a file's modification time into the past by a real number of seconds."""
    when = time.time() - seconds
    os.utime(path, (when, when))


def test_a_piece_written_after_the_last_commit_says_nothing(tmp_path: Path) -> None:
    """Mid-writing is not a fault, and a surface that cannot tell the difference is noise."""
    repo = _new_repo(tmp_path)
    (repo / "dreams" / "still-writing.md").write_text("half a thought\n", encoding="utf-8")

    result = _run_hook(repo)

    assert result.stderr.strip() == "", (
        "the hook spoke about writing that has not yet had a commit go past it, "
        "which is the habituation failure this design exists to avoid:\n"
        f"{result.stderr}"
    )


def test_a_piece_left_behind_by_a_later_commit_is_named(tmp_path: Path) -> None:
    repo = _new_repo(tmp_path)
    stranded = repo / "dreams" / "left-behind.md"
    stranded.write_text("a whole thought\n", encoding="utf-8")
    _age(stranded, 3600)

    # Something else gets saved. The dream does not.
    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "saved something else")

    result = _run_hook(repo)

    assert "left-behind.md" in result.stderr, (
        "a piece of writing survived a commit without being saved and the hook "
        f"said nothing:\n{result.stderr}"
    )
    assert "ONE tree" in result.stderr, (
        "the hook named stranded writing without saying that it only looks at one "
        "tree, so a clean run would read as proof of none"
    )


def test_writing_that_was_saved_is_not_named(tmp_path: Path) -> None:
    """The control. Without it, a hook that names every file in the directory passes above."""
    repo = _new_repo(tmp_path)
    saved = repo / "dreams" / "saved.md"
    saved.write_text("a whole thought\n", encoding="utf-8")
    _age(saved, 3600)
    _git(repo, "add", "dreams/saved.md")
    _git(repo, "commit", "-q", "-m", "saved the dream")

    result = _run_hook(repo)

    assert "saved.md" not in result.stderr, (
        f"the hook named writing that is committed:\n{result.stderr}"
    )


def test_it_is_scoped_to_writing_and_not_to_the_whole_tree(tmp_path: Path) -> None:
    """Untracked code is caught by other things. Pointing this at everything makes it wallpaper."""
    repo = _new_repo(tmp_path)
    scratch = repo / "scratch.py"
    scratch.write_text("x = 1\n", encoding="utf-8")
    _age(scratch, 3600)

    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "saved something else")

    result = _run_hook(repo)

    assert "scratch.py" not in result.stderr, (
        f"the hook reached outside personal writing:\n{result.stderr}"
    )


def test_outside_a_repository_it_says_nothing_rather_than_guessing() -> None:
    """NOT tmp_path, and that is the whole point of this test's history.

    The first version used pytest's tmp_path, which this project configures to
    live INSIDE the checkout. So the directory named "not-a-repo" was inside a
    repository, git resolved a root, and the hook correctly reported six
    hundred stranded files. I read that as the hook being broken and edited it.

    The directory was the right KIND of object and not the one I named. So the
    premise is asserted below before anything is concluded from it.
    """
    outside = Path(tempfile.mkdtemp(prefix="not-a-repo-"))
    try:
        probe = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=outside,
            capture_output=True,
            text=True,
        )
        assert probe.returncode != 0, (
            "this directory is inside a repository, so it cannot test the "
            f"outside-a-repository case: {probe.stdout.strip()}"
        )

        result = subprocess.run(
            [_bash(), str(HOOK)],
            cwd=outside,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert "[unsaved-writing]" not in result.stderr
    finally:
        shutil.rmtree(outside, ignore_errors=True)  # fail-soft: teardown cannot change a verdict


@pytest.mark.parametrize("directory", ["dreams", "exploration"])
def test_every_writing_directory_it_claims_is_actually_watched(
    tmp_path: Path, directory: str
) -> None:
    """A directory named in the scope list but never exercised is a claim nobody checked."""
    repo = _new_repo(tmp_path)
    stranded = repo / directory / "piece.md"
    stranded.write_text("a whole thought\n", encoding="utf-8")
    _age(stranded, 3600)

    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "saved something else")

    result = _run_hook(repo)

    assert f"{directory}/piece.md" in result.stderr, (
        f"{directory} is in the hook's scope list but stranded writing there was "
        f"not reported:\n{result.stderr}"
    )
