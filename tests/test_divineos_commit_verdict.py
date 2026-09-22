"""Running a command is not reading its answer.

2026-09-19. I told Andrew I had committed a repair. That commit does not exist
anywhere in the repository. I wrote the message, ran the command, read the
first lines of its output and reported success -- and the command had produced
nothing, because an automatic checkpoint had swept the change seconds earlier
and left the index empty.

The work survived; my reasoning did not. The diff reached the remote inside a
commit titled "auto-commit (post-extract): work in progress", carrying none of
the explanation I had written.

Three instances of one class in a single day: twice I missed the push
wrapper's verdict line, once this. The common move is reading the top of an
output and reporting the bottom. "Read more carefully" is the thing that had
already failed twice by then, and the failure is silent by construction -- a
commit that does not happen fires no post-commit hook, because git runs those
only when a commit occurs. Nothing fires when nothing happens.

So the check has to BE the commit, and its answer has to be the LAST line, the
same shape scripts/divineos_push.sh uses for the same reason.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "divineos_commit.sh"


def _bash() -> str:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ):
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q", "--initial-branch=main", str(tmp_path)], check=True)
    _git(tmp_path, "config", "user.email", "test@test")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(tmp_path, "add", "seed.txt")
    _git(tmp_path, "commit", "-qm", "first")
    return tmp_path


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_bash(), str(SCRIPT), *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_an_empty_index_is_refused_rather_than_reported_as_a_commit(repo):
    """The exact state that fooled me. Git's own output there is a branch line
    and a list of untracked files -- no commit line at all -- which reads like
    success if you stop before the end."""
    result = _run(repo, "-m", "a message that should reach no commit")

    assert result.returncode != 0
    assert "NOT COMMITTED (empty index)" in result.stdout
    # And the verdict must be the LAST line, so a truncated tail still carries it.
    assert result.stdout.strip().splitlines()[-1].endswith("NOT COMMITTED (empty index)")


def test_a_real_commit_is_verified_by_reading_it_back(repo):
    (repo / "thing.txt").write_text("content\n", encoding="utf-8")
    _git(repo, "add", "thing.txt")

    result = _run(repo, "-m", "a subject I actually wrote")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "a subject I actually wrote" in result.stdout
    assert result.stdout.strip().splitlines()[-1].endswith("COMMITTED+VERIFIED")


def test_a_moved_head_is_not_proof_the_commit_is_mine(repo):
    """The sharpest case, and the one the day actually produced.

    The checkpoint moves HEAD too. A wrapper that only asked "did HEAD move"
    would have answered yes on the very day my message reached no commit at
    all. So it reads the SUBJECT back and refuses to call the checkpoint's
    commit mine -- the difference between "I committed" and "something
    committed".
    """
    (repo / "thing.txt").write_text("content\n", encoding="utf-8")
    _git(repo, "add", "thing.txt")
    result = _run(repo, "-m", "auto-commit (post-extract): work in progress")

    assert result.returncode == 2
    assert "not yours" in result.stdout
    assert result.stdout.strip().splitlines()[-1].endswith("COMMITTED BUT NOT YOURS")


def test_outside_a_repository_it_says_so_rather_than_guessing():
    """Could-not-look is its own answer here too. A wrapper that cannot find a
    repository must not report either outcome about a commit.

    NOT USING tmp_path, AND THE REASON IS A FACT ABOUT THIS REPO. Pytest's
    temporary directories are configured to live INSIDE the checkout
    (tmp/pytest/...), so from one of them git always finds a repository and
    "outside any repository" is unreachable by construction. The first version
    of this test asked tmp_path for that state, got the empty-index answer
    instead, and I nearly adjusted the assertion to match -- which would have
    quietly deleted the only test of the could-not-look branch.

    So it makes a directory in the SYSTEM temp area, and if that somehow sits
    inside a repository too, it skips rather than asserting something it did
    not arrange.
    """
    import tempfile

    probe = Path(tempfile.mkdtemp())
    try:
        inside = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(probe),
            capture_output=True,
            text=True,
            check=False,
        )
        if inside.returncode == 0:
            pytest.skip(f"system temp is inside a repository ({inside.stdout.strip()})")

        result = subprocess.run(
            [_bash(), str(SCRIPT), "-m", "anything"],
            cwd=str(probe),
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 3
        assert "INFRASTRUCTURE ERROR" in result.stdout
    finally:
        shutil.rmtree(probe, ignore_errors=True)  # fail-soft: cleanup noise, never a finding.
