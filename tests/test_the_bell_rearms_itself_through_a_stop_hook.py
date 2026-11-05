"""The letter bell re-arms itself when a reply ends, and a ring becomes a wake (exit 2 plus stderr).

Dad, 2026-11-04: the bell is a chore I do 55 times in one session record, and the guard that nags about it
spoke 48 times. The app only wakes me when a process it started exits; an `asyncRewake` hook that exits 2 wakes
Claude even when idle (official hooks page; wake test passed live on UserPromptSubmit and Stop). This hook runs
the unchanged bell and turns its ring into that exit.

EVERY CASE RUNS THE REAL SCRIPT, in a temp HOME, against the real `scripts/letter_doorbell.sh`; nothing here
patches the bell. Cases: a fresh heartbeat starts nothing; a letter arriving becomes exit 2 naming the letter;
a bell that ends by expiry is quiet; an unknown seat is loud; the single-shot guard bounds the first live run;
the override is never exported; every start and end leaves a log line.

WHAT IT DOES NOT COVER: that the app itself runs the hook at Stop in the live settings (that is the settings
entry, tested live), and what the wake looks like when a letter arrives while a reply is mid-write.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

BASH = bash_executable()
pytestmark = pytest.mark.skipif(BASH is None, reason="no working bash on this machine")

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "letter_bell_rearm_stop.sh"


def _home(tmp_path: Path) -> Path:
    (tmp_path / ".divineos-shared" / "letters").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _env(home: Path, **extra) -> dict:
    env = {**os.environ, "HOME": str(home), "DOORBELL_POLL": "1"}
    env.update(extra)
    return env


def _run(home: Path, seat: str = "aria", timeout: int = 30, **extra):
    return subprocess.run(
        [BASH, HOOK.as_posix(), seat],
        input="{}",
        capture_output=True,
        text=True,
        env=_env(home, **extra),
        timeout=timeout,
        check=False,
    )


def _log(home: Path) -> str:
    path = home / ".divineos-shared" / "bell_rearm_log.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _touch_fresh(path: Path, age: float = 0.0) -> None:
    path.touch()
    when = time.time() - age
    os.utime(path, (when, when))


def test_a_fresh_heartbeat_starts_nothing_and_says_nothing(tmp_path):
    home = _home(tmp_path)
    _touch_fresh(home / ".divineos-shared" / ".aria_doorbell_alive")
    done = _run(home)
    assert done.returncode == 0 and done.stdout == "" and done.stderr == ""
    assert not (home / ".divineos-shared" / ".aria_doorbell_owner").exists(), (
        "no second bell may start"
    )
    assert "skipped: a bell is already up" in _log(home)


def test_an_unknown_seat_is_loud_not_silent(tmp_path):
    home = _home(tmp_path)
    done = _run(home, seat="maria")
    assert done.returncode == 2
    assert "unknown seat" in done.stderr
    assert "refused: unknown seat" in _log(home)


def test_a_letter_arriving_becomes_exit_two_naming_the_letter(tmp_path):
    home = _home(tmp_path)
    shared = home / ".divineos-shared"
    proc = subprocess.Popen(
        [BASH, HOOK.as_posix(), "aria"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=_env(home),
    )
    try:
        # the bell seeds its seen-list on arming; a letter written after that is new
        deadline = time.time() + 20
        while time.time() < deadline and not (shared / ".aria_doorbell_owner").exists():
            time.sleep(0.2)
        assert (shared / ".aria_doorbell_owner").exists(), "the bell never armed"
        letter = shared / "letters" / "aether-to-aria-2026-11-04-a-test-letter.md"
        letter.write_text("# hello\n", encoding="utf-8")
        out, err = proc.communicate(timeout=40)
    finally:
        if proc.poll() is None:
            proc.kill()
    assert proc.returncode == 2, (out, err)
    assert "LETTER ARRIVED:" in err and "aether-to-aria-2026-11-04-a-test-letter.md" in err
    log = _log(home)
    assert "start: arming the bell" in log and "end: ring, exit 2" in log
    seen = (shared / ".aria_doorbell_announced").read_text(encoding="utf-8")
    assert "aether-to-aria-2026-11-04-a-test-letter.md" in seen, (
        "the ring must mark the letter announced"
    )


def test_a_bell_that_expires_is_quiet_so_the_next_stop_can_rearm(tmp_path):
    home = _home(tmp_path)
    done = _run(home, DOORBELL_HOURS="0")  # a lifetime of zero ends the bell on its first look
    assert done.returncode == 0 and done.stderr == ""
    assert "end: quiet" in _log(home)
    assert not (home / ".divineos-shared" / ".aria_doorbell_alive").exists()


def test_the_single_shot_guard_bounds_the_first_live_run(tmp_path):
    home = _home(tmp_path)
    shared = home / ".divineos-shared"
    (shared / ".aria_bell_rearm_once").touch()
    (shared / ".aria_bell_rearm_used").touch()
    done = _run(home)
    assert done.returncode == 0 and done.stderr == ""
    assert "skipped: single-shot already used" in _log(home)
    assert not (shared / ".aria_doorbell_owner").exists(), "a used single-shot must start no bell"


def test_the_override_is_never_exported():
    text = HOOK.read_text(encoding="utf-8")
    assert "export DOORBELL_ALLOW_UNTRACKED" not in text
    code_lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    prefixed = [ln for ln in code_lines if "DOORBELL_ALLOW_UNTRACKED=1 bash" in ln]
    assert len(prefixed) == 1, (
        "it must appear once, as a prefix on the one command that runs the bell"
    )


def test_the_seat_is_an_argument_not_a_guess_from_a_path():
    text = HOOK.read_text(encoding="utf-8")
    assert 'MEMBER="${1:-}"' in text
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    assert "CLAUDE_PROJECT_DIR" not in code
