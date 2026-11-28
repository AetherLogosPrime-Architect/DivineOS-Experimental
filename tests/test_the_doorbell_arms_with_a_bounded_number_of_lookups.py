"""Arming the bell must cost a handful of directory lookups, never one per letter.

Aletheia's live run of #776 (2026-11-27): against 2,417 real letters the arm-time "already answered" pass
spawned one `find` per file, took more than nine minutes, and had marked 1,157 letters when it was stopped.
No bell listens while it arms, so a pass that scales with the folder leaves the seat deaf for as long as
the folder is big. The unit tests on a handful of letters could not see it.

This pins the shape, not a stopwatch: a `find` shim in front of PATH logs every call, and the number of calls
made by the time the bell says it is armed must stay constant as the folder grows. A stopwatch would pass on a
fast Linux CI and fail on this machine, which is the wrong way round for a bug that only hurts here."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BELL = ROOT / "scripts" / "letter_doorbell.sh"
BASH = shutil.which("bash")
REAL_FIND = shutil.which("find")
REAL_GREP = shutil.which("grep")

pytestmark = pytest.mark.skipif(
    BASH is None or REAL_FIND is None or REAL_GREP is None,
    reason="no bash, find or grep to run the bell with",
)

MAX_FINDS = (
    8  # a constant: one listing and a few fixed greps, plus slack; never a number that grows
)


def _letter(path: Path, age_secs: int) -> None:
    path.write_text("x", encoding="utf-8")
    t = time.time() - age_secs
    os.utime(path, (t, t))


def _arm(
    tmp_path: Path, pairs: int, patience: float = 120.0, linked: bool = False
) -> tuple[str, int, list[str]]:
    """Arm the bell as aether against `pairs` answered letters; return (output, find calls, marker).

    The bell never exits on its own, so the test lets it finish: it waits for the armed line, reads the
    find-call count at that moment, then drops one unannounced letter so the bell rings and exits."""
    shared = tmp_path / ".divineos-shared"
    letters = shared / "letters"
    if linked:
        # The letters folder itself is a link (a house can keep it elsewhere): `find` does not follow a
        # link given as its starting point unless told to, and without that the pass saw an empty folder.
        real = tmp_path / "real_letters"
        real.mkdir(parents=True)
        shared.mkdir(parents=True)
        letters.symlink_to(real, target_is_directory=True)
    else:
        letters.mkdir(parents=True)
    (shared / ".aether_doorbell_announced").write_bytes(b"aria-to-aether-2026-01-01-ancient.md\n")
    for i in range(pairs):
        _letter(letters / f"aria-to-aether-2026-11-03-in{i:04d}.md", 500)
        time.sleep(0.002)
    time.sleep(0.05)
    _letter(
        letters / "aether-to-aria-2026-11-03-reply.md", 100
    )  # my reply, after all of them arrived

    shim_dir = tmp_path / "shim"
    shim_dir.mkdir()
    log = tmp_path / "find_calls.log"
    # `find` and `grep` are the two tools a per-letter loop reaches for; both are counted into one log.
    for tool, real in (("find", REAL_FIND), ("grep", REAL_GREP)):
        shim = shim_dir / tool
        shim.write_text(
            f'#!/bin/bash\necho "{tool} $@" >> "{log.as_posix()}"\nexec "{Path(real).as_posix()}" "$@"\n',
            encoding="utf-8",
        )
        shim.chmod(shim.stat().st_mode | stat.S_IEXEC)

    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "DOORBELL_ALLOW_UNTRACKED": "1",
        "DOORBELL_POLL": "1",
        "PATH": f"{shim_dir.as_posix()}{os.pathsep}{os.environ['PATH']}",
    }
    out_file = tmp_path / "bell_out.txt"
    with out_file.open("w", encoding="utf-8") as sink:
        proc = subprocess.Popen(
            [BASH, "-c", f'bash "{BELL.as_posix()}" aether'],
            env=env,
            stdout=sink,
            stderr=subprocess.STDOUT,
        )
        calls = -1
        deadline = time.time() + patience
        try:
            while time.time() < deadline:
                if "doorbell armed" in out_file.read_text(encoding="utf-8", errors="ignore"):
                    calls = len(log.read_text(encoding="utf-8").splitlines()) if log.exists() else 0
                    break
                time.sleep(0.2)
            # Ring it, so the bell exits by itself and nothing is left running.
            _letter(letters / "aria-to-aether-2026-12-31-the-ring.md", 0)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
        finally:
            if proc.poll() is None:
                proc.kill()
    out = out_file.read_text(encoding="utf-8", errors="ignore")
    marker = (shared / ".aether_doorbell_announced").read_text(encoding="utf-8").splitlines()
    return out, calls, marker


def test_arming_makes_a_constant_number_of_find_calls_however_many_letters(tmp_path):
    out_small, calls_small, _ = _arm(tmp_path / "small", 4)
    out_big, calls_big, _ = _arm(tmp_path / "big", 40)
    assert "doorbell armed" in out_small and "doorbell armed" in out_big, (out_small, out_big)
    # Control: the shim sees calls at all, or "0 calls" would pass for the wrong reason.
    assert calls_small >= 1 and calls_big >= 1, (calls_small, calls_big)
    assert calls_big <= MAX_FINDS, (
        f"{calls_big} find calls for 40 letters: it scales with the folder"
    )
    assert calls_big <= calls_small + 1, (calls_small, calls_big)


def test_a_letters_folder_that_is_a_link_still_has_its_answered_letters_marked(tmp_path):
    try:
        _, _, marker = _arm(tmp_path, 6, linked=True)
    except (
        OSError
    ) as exc:  # no symlink privilege on this machine (WinError 1314): cannot make the case
        pytest.skip(f"cannot create a symlink here: {exc}")
    answered = [m for m in marker if m.startswith("aria-to-aether-2026-11-03-in")]
    assert len(answered) == 6, f"{len(answered)} of 6 marked through a linked folder: {marker[:3]}"


def test_the_answered_letters_are_still_marked_after_the_rewrite(tmp_path):
    _, _, marker = _arm(tmp_path, 12)
    answered = [m for m in marker if m.startswith("aria-to-aether-2026-11-03-in")]
    assert len(answered) == 12, f"{len(answered)} of 12 answered letters were marked: {marker[:3]}"
