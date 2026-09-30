"""The stop-time reader for push state, and the four meanings its silence used to carry.

It was built to refuse one claim: that work landed when it had not. It was
silent in every other case, so "a push was never attempted", "the last one
succeeded" and "a refusal on file is no longer true" all arrived as nothing at
all -- the same nothing as everything-is-fine.

The stale-refusal case is the one with a story. I quoted a refusal to Aria that
had stopped being true, and nothing in the room aged it, because this file goes
quiet the moment the work lands.

Real repositories and a real remote on disk. Nothing here mocks git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

HOOK = (
    Path(__file__).resolve().parents[1]
    / ".claude"
    / "hooks"
    / "unlanded-push-must-not-close-quiet.sh"
)


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

    Asking for bash by name on this box can return the WSL relay, which exists,
    runs, and cannot execute a Windows-path script -- failing onto the same
    channel the hook speaks on, so every absence assertion here would pass.
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
    """A control that cannot be built must FAIL rather than skip."""
    assert BASH is not None, (
        "no bash on this machine can run a Windows-path script, so this hook "
        "cannot be exercised. That is untested, not passing."
    )
    return BASH


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _repo_with_remote(tmp_path: Path) -> Path:
    """A clone whose origin is a real repository on disk, so ls-remote answers truthfully."""
    bare = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-q", str(bare))

    repo = tmp_path / "work"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "trunk")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    _git(repo, "remote", "add", "origin", str(bare))
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")
    _git(repo, "push", "-q", "origin", "trunk")
    return repo


def _run_hook(repo: Path, home: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DIVINEOS_HOME"] = str(home)
    result = subprocess.run([_bash(), str(HOOK)], cwd=repo, capture_output=True, text=True, env=env)
    assert "execvpe" not in result.stderr and "CreateProcessCommon" not in result.stderr, (
        f"the interpreter never ran the hook:\n{result.stderr}"
    )
    return result


def _verdict(home: Path, text: str) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "push_verdict.txt").write_text(text, encoding="utf-8")


def test_a_refusal_the_server_contradicts_is_called_stale(tmp_path: Path) -> None:
    """The case that came from quoting a refusal that had stopped being true."""
    repo = _repo_with_remote(tmp_path)
    home = tmp_path / "home"
    _verdict(home, "REFUSED: moved revision\n")

    result = _run_hook(repo, home)

    assert "STALE" in result.stderr, (
        "a refusal on file that the server contradicts produced no line, which is "
        f"the silence that lets a remembered refusal survive:\n{result.stderr}"
    )


def test_work_never_pushed_is_named_even_with_no_verdict_at_all(tmp_path: Path) -> None:
    """A push that never ran writes no verdict, which used to end this file's job."""
    repo = _repo_with_remote(tmp_path)
    home = tmp_path / "home-empty"
    home.mkdir()
    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "work that was never pushed")

    result = _run_hook(repo, home)

    assert "NOT ON ORIGIN" in result.stderr, (
        "unpushed work with no verdict file produced nothing, which is the "
        f"never-attempted case hiding inside everything-is-fine:\n{result.stderr}"
    )


def test_an_empty_verdict_is_not_the_same_answer_as_a_missing_one(tmp_path: Path) -> None:
    """A collapse introduced while repairing another one, caught by the test above.

    The wrapper truncates the file at the start of every run, so an EMPTY file
    means a push began and did not finish. A file that is not there means no
    push has ever been recorded here. Defaulting both to the same empty string
    made the never-ran case wear the interrupted case's words.
    """
    repo = _repo_with_remote(tmp_path)
    home = tmp_path / "home-inflight"
    _verdict(home, "")
    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "work a running push has not carried yet")

    result = _run_hook(repo, home)

    assert "HAS NOT FINISHED" in result.stderr, (
        f"an empty verdict stopped meaning began-and-did-not-finish:\n{result.stderr}"
    )


def test_a_refusal_that_is_still_true_keeps_its_stronger_wording(tmp_path: Path) -> None:
    """The original case. Without it, the rewrite could collapse both into one line."""
    repo = _repo_with_remote(tmp_path)
    home = tmp_path / "home-refused"
    _verdict(home, "REFUSED: moved revision\n")
    (repo / "seed.txt").write_text("seed\nmore\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "work the refusal is about")

    result = _run_hook(repo, home)

    assert "THE LAST PUSH WAS REFUSED" in result.stderr, result.stderr


def test_a_successful_push_with_everything_landed_says_nothing(tmp_path: Path) -> None:
    """The control, and the only state silence is now allowed to mean."""
    repo = _repo_with_remote(tmp_path)
    home = tmp_path / "home-ok"
    _verdict(home, "OK: pushed\n")

    result = _run_hook(repo, home)

    assert result.stderr.strip() == "", (
        f"the hook spoke when there was nothing to report:\n{result.stderr}"
    )
