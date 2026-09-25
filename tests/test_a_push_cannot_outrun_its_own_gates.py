"""The gates decide about the state they were handed, not the state that travels.

Those two are separated by however long the checks take, and the slowest check
in this house is the full test suite — so the window is widest exactly where
the checking is most thorough. Recorded twice, in opposite directions: once a
transfer carried a state older than fixes made during the run, once a commit
made during the run reached the remote while the gates had examined its parent.

The two instances disagree about when git resolves a ref. This check does not
depend on the answer — it compares what the hook was handed against what the
ref says now, so it fires whichever side moved. These tests pin that, and pin
the two silences that must stay silences: no ref list, and a revision with no
ref to re-read.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK = REPO_ROOT / "scripts" / "check_ref_did_not_move.sh"


def _working_bash() -> str | None:
    """A bash that can actually run a script, proven rather than resolved.

    Asking for bash by name on this box can return the WSL relay, which exists,
    runs, and cannot execute a Windows-path script.
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

pytestmark = [
    pytest.mark.skipif(not CHECK.exists(), reason="check absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
]


def _run(stdin_text: str, cwd: Path) -> subprocess.CompletedProcess:
    assert BASH is not None
    return subprocess.run(
        [BASH, str(CHECK)],
        input=stdin_text,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=60,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway repository with two commits, so a ref can be stale on purpose."""
    work = tmp_path / "work"
    work.mkdir()
    run = lambda *a: subprocess.run(a, cwd=str(work), capture_output=True, check=True)  # noqa: E731
    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")
    (work / "f.txt").write_text("one", encoding="utf-8")
    run("git", "add", "f.txt")
    run("git", "commit", "-q", "-m", "first")
    (work / "f.txt").write_text("two", encoding="utf-8")
    run("git", "commit", "-q", "-a", "-m", "second")
    return work


def _rev(repo: Path, spec: str) -> str:
    out = subprocess.run(
        ["git", "rev-parse", spec], cwd=str(repo), capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def test_an_unmoved_ref_passes(repo: Path) -> None:
    """The ordinary case. This is the control: if it ever fails, the check is
    refusing everything and the refusing test below proves nothing."""
    tip = _rev(repo, "refs/heads/main")
    result = _run(f"refs/heads/main {tip} refs/heads/main {tip}\n", repo)
    assert result.returncode == 0, result.stderr


def test_a_ref_that_moved_is_refused(repo: Path) -> None:
    """The failure that has happened twice: the gates examined one revision and
    another is what would travel."""
    stale = _rev(repo, "refs/heads/main^")
    result = _run(f"refs/heads/main {stale} refs/heads/main {stale}\n", repo)
    assert result.returncode != 0
    assert "REFUSING" in result.stderr


def test_the_refusal_names_both_revisions(repo: Path) -> None:
    """Naming them is what makes looking cheaper than re-running blind. A
    generic refusal trains the ignoring this exists to prevent."""
    stale = _rev(repo, "refs/heads/main^")
    tip = _rev(repo, "refs/heads/main")
    result = _run(f"refs/heads/main {stale} refs/heads/main {stale}\n", repo)
    assert stale in result.stderr
    assert tip in result.stderr


def test_no_ref_list_is_silence_not_approval(repo: Path) -> None:
    """Run by hand or outside the hook there is nothing to compare, and this
    check has nothing to say. The other gates decide on their own evidence."""
    result = _run("", repo)
    assert result.returncode == 0, result.stderr


def test_a_deletion_is_skipped(repo: Path) -> None:
    """A deletion carries an all-zero revision and has no tip to re-read."""
    zeros = "0" * 40
    result = _run(f"(delete) {zeros} refs/heads/gone {_rev(repo, 'HEAD')}\n", repo)
    assert result.returncode == 0, result.stderr


def test_an_unresolvable_ref_is_skipped(repo: Path) -> None:
    """A revision pushed directly has no ref to re-resolve, so there is no
    moving target to catch and skipping is the honest answer."""
    tip = _rev(repo, "HEAD")
    result = _run(f"refs/heads/does-not-exist {tip} refs/heads/x {tip}\n", repo)
    assert result.returncode == 0, result.stderr
