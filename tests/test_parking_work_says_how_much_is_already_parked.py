"""Parking work must say how much is already parked and never came back.

THE DEFECT, measured 2026-09-21. Fifty-two parked change-sets sat in this
repository, the oldest four months old, and nothing in the house listed or
counted them. A hundred and forty pieces of writing -- letters, explorations, a
proposal -- existed on no branch and nowhere on disk, only inside those parked
sets. Confirmed by hashing every markdown on the machine and comparing content
rather than filenames, after two shallower checks gave larger and wrong answers.

Parking is the one operation whose OUTPUT is a clean working tree, so every
surface that looks for unfinished work reports all-clear immediately afterwards.
The tidiness is the camouflage.

WHY IT SPEAKS WHEN IT DOES, and this is the whole design. It does not announce
the pile every turn -- a line that prints unconditionally becomes furniture
within a day and is then decoration rather than an instrument. It speaks at the
moment the pile GROWS, because that is when the intention "I will come back to
this shortly" is formed, and the useful thing to know right then is how many
previous such intentions are still outstanding.

VISIBILITY, NOT ENFORCEMENT. Aria's rule for her letter tripwire, and it holds
here: this must never block parking. Parking is correct and necessary. What was
missing was anybody being told.

Real repositories, real stashes. Nothing here mocks git.
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
    / "parked-work-must-not-be-invisible.sh"
)


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

    Bare `bash` here can resolve to the WSL relay, which exists, runs, and
    cannot execute a Windows-path script -- it fails onto stderr, which the
    silence assertions below would read as silence.
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

    Three assertions here are absence assertions. If the hook never runs they
    pass trivially and this file reports green while testing nothing.
    """
    if BASH is None:
        pytest.fail("no bash on this box could run a script; the hook never ran")
    return BASH


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, timeout=60)


def _repo(tmp: str) -> Path:
    repo = Path(tmp) / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "Test")
    (repo / "seed.txt").write_text("seed", encoding="utf-8")
    _git(repo, "add", "seed.txt")
    _git(repo, "commit", "-q", "-m", "seed")
    assert _git(repo, "rev-parse", "HEAD").returncode == 0, "the fixture repo is not real"
    return repo


def _park(repo: Path, name: str, label: str) -> None:
    (repo / name).write_text("work in progress\n", encoding="utf-8")
    _git(repo, "add", name)
    res = _git(repo, "stash", "push", "-m", label)
    assert res.returncode == 0, f"the fixture parked nothing: {res.stderr}"


def _invoke(repo: Path, since: float) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [_bash(), str(HOOK)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=repo,
        input="",
        env={**os.environ, "PARKED_WORK_SINCE_EPOCH": str(int(since))},
    )
    combined = proc.stdout + proc.stderr
    assert "execvpe" not in combined and "CreateProcessCommon" not in combined, (
        f"the shell could not launch the hook, so nothing was tested: {combined!r}"
    )
    return proc


def _run(repo: Path, since: float) -> str:
    proc = _invoke(repo, since)
    assert proc.returncode == 0, f"this surface must never block; it exited {proc.returncode}"
    return (proc.stdout + proc.stderr).strip()


def test_a_repository_with_nothing_parked_is_silent() -> None:
    """The silence case, written first. It carries the claim."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        assert _run(repo, time.time() - 60) == ""


def test_an_old_pile_alone_does_not_speak_every_turn() -> None:
    """A line that prints unconditionally is furniture within a day.

    Work parked before this session is real, and it is not news on every turn.
    The pile alone must stay quiet.
    """
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        _park(repo, "old_a.txt", "parked a while ago")
        _park(repo, "old_b.txt", "also a while ago")
        # The session began AFTER both were parked.
        assert _run(repo, time.time() + 60) == ""


def test_parking_something_new_names_the_pile_it_joined() -> None:
    """The moment the intention forms is the moment to say what is outstanding."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        _park(repo, "old_a.txt", "parked a while ago")
        _park(repo, "old_b.txt", "also a while ago")
        since = time.time() - 60
        _park(repo, "new_one.txt", "parked just now")
        out = _run(repo, since)
    assert out, "parking something new produced no line at all"
    assert "3" in out, f"the size of the pile it joined is not named: {out!r}"


def test_outside_a_repository_it_is_silent_and_scans_nothing() -> None:
    """The root-guard lesson, already paid for once.

    Reading an empty repository root into a bare `cd` succeeds and stays put,
    so a hook can end up scanning whatever directory it launched from. The
    guard must reject the empty answer before moving.
    """
    tmp = tempfile.mkdtemp()
    try:
        plain = Path(tmp) / "not_a_repo"
        plain.mkdir()
        probe = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=plain,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert probe.returncode != 0, "this directory IS a repo, so the control is dead"
        assert _run(plain, time.time() - 60) == ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_it_never_blocks_even_when_it_speaks() -> None:
    """Visibility, not enforcement. Parking is correct; nobody was being told."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = _repo(tmp)
        since = time.time() - 60
        _park(repo, "new_one.txt", "parked just now")
        proc = _invoke(repo, since)
    assert proc.returncode == 0, f"a visibility surface must exit clean; got {proc.returncode}"
    assert (proc.stdout + proc.stderr).strip(), "it exited clean but said nothing"
