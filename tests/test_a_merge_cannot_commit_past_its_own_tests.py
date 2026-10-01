"""A merge presents one comparison and it is not the one that decides.

Resolving a conflict puts two sides in front of me and invites a choice between
them. That can be done thoroughly while being the wrong question: what decides
correctness is each side against the BEHAVIOUR of the module it lands in, and
nothing in a merge ever presents that comparison.

2026-09-20: I spliced two versions of a message together having checked they
said the same thing as text. My branch removes the limitation the longer one
explains, so the result would have told a reader that a real miss was an
inapplicable question. An inherited test caught it. My reading did not.

THE GUARD IS UNPROVEN UNTIL A LIVE MERGE IS ACTUALLY REFUSED BY IT, which is
what these cases are for. A script that exists, parses and is wired into the
commit path is still only a claim; the claim is that it stops a commit, and the
only evidence for that is a commit it stopped.

Four cases against real repositories rather than a stand-in for git: the
refusal, the control that must pass through the same machinery, the silence
outside a merge, and an absence of coverage reported as an absence rather than
as a clean result.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
GUARD = REPO_ROOT / "scripts" / "check_merge_resolution_tested.sh"


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

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
    pytest.mark.skipif(not GUARD.exists(), reason="guard absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
    pytest.mark.skipif(shutil.which("git") is None, reason="no git on this platform"),
]


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, timeout=120)


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    subprocess.run(
        ["git", "init", "--initial-branch=main", str(repo)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    _git("config", "user.email", "test@test", cwd=repo)
    _git("config", "user.name", "test", cwd=repo)
    return repo


def _commit(repo: Path, message: str) -> None:
    _git("add", "-A", cwd=repo)
    result = _git("commit", "--no-verify", "-m", message, cwd=repo)
    assert result.returncode == 0, result.stdout + result.stderr


def _conflicting_merge(repo: Path) -> None:
    """Leave `repo` in a live merge with the module still unresolved."""
    (repo / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "tests" / "test_mod.py").write_text(
        "from mod import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    _commit(repo, "base")
    _git("checkout", "-b", "side", cwd=repo)
    (repo / "mod.py").write_text("VALUE = 2\n", encoding="utf-8")
    _commit(repo, "side")
    _git("checkout", "main", cwd=repo)
    (repo / "mod.py").write_text("VALUE = 3\n", encoding="utf-8")
    _commit(repo, "main")
    merge = _git("merge", "--no-commit", "side", cwd=repo)
    assert merge.returncode != 0, "expected a conflict, got a clean merge"
    assert (repo / ".git" / "MERGE_HEAD").exists(), "no live merge to check"


def _resolve(repo: Path, value: str) -> None:
    (repo / "mod.py").write_text(f"VALUE = {value}\n", encoding="utf-8")
    _git("add", "mod.py", cwd=repo)


def _run_guard(repo: Path) -> subprocess.CompletedProcess:
    assert BASH is not None
    return subprocess.run(
        [BASH, str(GUARD)], capture_output=True, text=True, cwd=str(repo), timeout=300
    )


def test_a_resolution_its_own_test_rejects_is_refused(tmp_path: Path):
    """The whole point: the resolution parses, reads fine, and is wrong."""
    repo = _repo(tmp_path)
    _conflicting_merge(repo)
    _resolve(repo, "3")

    result = _run_guard(repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "REFUSED" in result.stderr, result.stderr


def test_a_resolution_its_own_test_accepts_passes(tmp_path: Path):
    """The control. Same machinery, same merge, a resolution that holds.

    Without this the case above only proves the guard can say no, which a
    guard that always says no would also satisfy.
    """
    repo = _repo(tmp_path)
    _conflicting_merge(repo)
    _resolve(repo, "1")

    result = _run_guard(repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "REFUSED" not in result.stderr


def test_outside_a_merge_it_says_nothing_at_all(tmp_path: Path):
    """No conflicted set to reason about, so silence is the correct answer."""
    repo = _repo(tmp_path)
    (repo / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit(repo, "base")

    result = _run_guard(repo)
    assert result.returncode == 0
    assert result.stderr.strip() == "", result.stderr


def test_no_covering_test_is_reported_as_absence_not_as_a_pass(tmp_path: Path):
    """A check that goes quiet reads as approval, and this one must not."""
    repo = _repo(tmp_path)
    (repo / "notes.md").write_text("one\n", encoding="utf-8")
    _commit(repo, "base")
    _git("checkout", "-b", "side", cwd=repo)
    (repo / "notes.md").write_text("two\n", encoding="utf-8")
    _commit(repo, "side")
    _git("checkout", "main", cwd=repo)
    (repo / "notes.md").write_text("three\n", encoding="utf-8")
    _commit(repo, "main")
    _git("merge", "--no-commit", "side", cwd=repo)
    (repo / "notes.md").write_text("three\n", encoding="utf-8")
    _git("add", "notes.md", cwd=repo)

    result = _run_guard(repo)
    assert result.returncode == 0
    assert "NOT a pass" in result.stderr, (
        "the guard went quiet on an uncovered merge, which reads as approval"
    )
