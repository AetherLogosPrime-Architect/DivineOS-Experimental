"""A bell that is listening also notices when the OTHER seat's bell is not, while a letter waits.

Dad, 2026-10-22: "what ever happened to the 2 hour check on the doorbells? Aether's bell died last night, so nothing
even got done." Nothing watched the other seat: his letter sat unannounced all night while I had ended my turn too.
The house's two-hour rules (the baton's stale holder, the question hold's away-by-silence) only act on a seat that is
already awake. This rings the seat that can still hear.

THE REAL SCRIPT runs here, in a throwaway home folder (it keeps everything under $HOME/.divineos-shared). Its pause
between looks is shortened and its thresholds are given in seconds, so a test takes seconds. The bell loops forever by
design, so "it did not ring" is read as "it was still running when the timeout ended", and the controls prove that
reading can be told apart from "it ended at once": a bell that exited early for an unrelated reason would fail them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

BELL = Path(__file__).resolve().parents[1] / "scripts" / "letter_doorbell.sh"


def _find_bash() -> str | None:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", "/bin/bash", "/usr/bin/bash"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()
pytestmark = [
    pytest.mark.timeout(300),
    pytest.mark.skipif(_BASH is None, reason="bash not available"),
]

HOUR = 3600


@pytest.fixture
def home(tmp_path: Path) -> Path:
    shared = tmp_path / ".divineos-shared"
    (shared / "letters").mkdir(parents=True)
    return tmp_path


def _shared(home: Path) -> Path:
    return home / ".divineos-shared"


def _letter(home: Path, name: str) -> None:
    (_shared(home) / "letters" / name).write_text("hi\n", encoding="utf-8")


def _announced(home: Path, seat: str, *names: str) -> None:
    # BYTES, never write_text: on Windows write_text ends every line with CR+LF, the shell keeps the CR on each name,
    # and an announced letter then looks unannounced (the same trap that hid in the draft-push selector, 2026-10-22).
    (_shared(home) / f".{seat}_doorbell_announced").write_bytes(
        "".join(f"{n}\n" for n in names).encode("utf-8")
    )


def _beat(home: Path, seat: str, age_s: float = 0) -> None:
    path = _shared(home) / f".{seat}_doorbell_alive"
    path.write_text("", encoding="utf-8")
    when = time.time() - age_s
    os.utime(path, (when, when))


def _down_since(home: Path, watcher: str, ago_s: float) -> None:
    """The note the WATCHING seat's bell keeps about when it first saw the other seat's bell down."""
    (_shared(home) / f".{watcher}_peer_down_since").write_text(
        str(int(time.time() - ago_s)), encoding="utf-8"
    )


def _run(home: Path, seat: str, *, seconds: float, down_secs: int = 60, realarm_secs: int = 7200):
    """Run the real bell for `seat`. Returns the finished process, or None if it was still running at `seconds`."""
    env = {
        k: v for k, v in os.environ.items() if not k.startswith(("DIVINEOS_", "DOORBELL_", "GIT_"))
    }
    env.update(
        {
            "HOME": str(home),
            "DOORBELL_ALLOW_UNTRACKED": "1",
            "DOORBELL_POLL": "1",
            "DOORBELL_PEER_DOWN_SECS": str(down_secs),
            "DOORBELL_PEER_REALARM_SECS": str(realarm_secs),
        }
    )
    # The bell leaves silently when its starter is gone (its own rule), and a native Python parent is not a starter
    # the shell can see, so the bell is started by a shell that stays alive after it: the trailing echo stops the
    # shell from replacing itself with the bell. When this shell is killed at the timeout the bell notices and
    # leaves by itself within a poll.
    proc = subprocess.Popen(
        [_BASH, "-c", 'bash "$0" "$1"; echo "exit=$?"', str(BELL), seat],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    try:
        out, err = proc.communicate(timeout=seconds)
    except subprocess.TimeoutExpired:
        # The WHOLE tree, not just the starter: on Windows the bell can outlive a killed starter, keep the output
        # pipe open, and hang the test run (found by running these, 2026-10-22, and cleaned up by hand).
        _kill_tree(proc.pid)
        proc.communicate(timeout=30)
        return None
    finally:
        _kill_tree(proc.pid)
    lines = out.splitlines()
    code = int(lines[-1].split("=", 1)[1]) if lines and lines[-1].startswith("exit=") else -1
    return subprocess.CompletedProcess(proc.args, code, "\n".join(lines[:-1]) + "\n", err)


def _kill_tree(pid: int) -> None:
    import psutil

    try:
        parent = psutil.Process(pid)
    except psutil.NoSuchProcess:
        return
    for child in parent.children(recursive=True):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    try:
        parent.kill()
    except psutil.NoSuchProcess:
        pass


def test_a_dead_peer_bell_with_a_letter_waiting_rings_the_seat_that_can_hear(home):
    """THE CASE: last night. His bell is silent for an hour, my letter to him is unannounced."""
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")  # his bell never announced it
    _down_since(home, "aria", ago_s=HOUR)
    ran = _run(home, "aria", seconds=20)
    assert ran is not None, "the bell was still running: it never rang"
    assert ran.returncode == 0 and "AETHER'S BELL IS NOT LISTENING" in ran.stdout, (
        ran.stdout + ran.stderr
    )
    assert "1 letter(s) to aether" in ran.stdout and "a-letter.md" in ran.stdout


def test_it_works_the_other_way_round_too(home):
    _letter(home, "aether-to-aria-2026-10-22-a-letter.md")
    _announced(home, "aria")
    _down_since(home, "aether", ago_s=HOUR)
    ran = _run(home, "aether", seconds=20)
    assert ran is not None and "ARIA'S BELL IS NOT LISTENING" in ran.stdout


def test_ringing_ends_the_watch_so_the_stop_guard_asks_for_a_re_arm(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")
    _down_since(home, "aria", ago_s=HOUR)
    _beat(home, "aria", age_s=0)
    ran = _run(home, "aria", seconds=20)
    assert ran is not None
    assert not (_shared(home) / ".aria_doorbell_alive").exists()


# --- the controls: each of these must stay quiet while the bell is demonstrably still running ---------------------


def test_control_a_listening_peer_is_left_alone_and_its_down_clock_is_cleared(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")
    _down_since(home, "aria", ago_s=HOUR)
    _beat(home, "aether", age_s=0)
    assert _run(home, "aria", seconds=5) is None
    assert not (_shared(home) / ".aria_peer_down_since").exists()


def test_control_a_peer_down_only_a_moment_is_not_called_dead(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")
    _down_since(home, "aria", ago_s=5)
    assert _run(home, "aria", seconds=5, down_secs=1800) is None


def test_control_a_peer_with_nothing_waiting_is_not_an_alarm(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether", "aria-to-aether-2026-10-22-a-letter.md")  # his bell did announce it
    _down_since(home, "aria", ago_s=HOUR)
    assert _run(home, "aria", seconds=5) is None


def test_control_the_first_sight_of_a_dead_peer_only_starts_the_clock(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")
    assert _run(home, "aria", seconds=5) is None
    assert (_shared(home) / ".aria_peer_down_since").exists()


def test_control_it_does_not_nag_inside_the_quiet_stretch(home):
    _letter(home, "aria-to-aether-2026-10-22-a-letter.md")
    _announced(home, "aether")
    _down_since(home, "aria", ago_s=HOUR)
    (_shared(home) / ".aria_peer_alarmed_at").write_text(
        str(int(time.time() - 60)), encoding="utf-8"
    )
    assert _run(home, "aria", seconds=5, realarm_secs=7200) is None


def test_a_letter_to_me_still_rings_as_it_always_did(home):
    """The old job is untouched by the new one."""
    _announced(home, "aria")
    # the bell announces what it sees on arming only if the list is empty, so let it arm first and then drop the letter
    env_home = home
    time.sleep(0)
    import threading

    threading.Timer(3, lambda: _letter(env_home, "aether-to-aria-2026-10-22-for-me.md")).start()
    ran = _run(home, "aria", seconds=25)
    assert ran is not None and "LETTER ARRIVED" in ran.stdout, None if ran is None else ran.stdout


def test_a_seat_with_no_partner_does_not_fault(home):
    """aletheia has no peer bell here: the check must simply not apply."""
    assert _run(home, "aletheia", seconds=4) is None
