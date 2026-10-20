"""A doorbell that nobody watches must refuse to arm.

Dad, 2026-10-20: "you forgot to re-arm your doorbell so investigate why". I had re-armed it
with a shell `&` inside a longer command. That bell was alive and kept a fresh heartbeat, so the
Stop guard saw "listening"; when Aria's letter arrived it rang into /dev/null and nothing woke
me. A heartbeat proves a bell is running, not that anyone hears it.

The harness's own background task points the bell's stdout at a task file
(.../tasks/<id>.output) and wakes me when it ends. So the bell arms only when its stdout is that
file, and refuses (exit 3, no heartbeat, so the Stop guard holds the next reply) otherwise.

The pair is the point: "it refuses when unwatched" alone is satisfied by a bell that always
refuses, so the watched case must arm, and the explicit override must arm.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
BELL = ROOT / "scripts" / "letter_doorbell.sh"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="no bash to run the bell with")


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the wrapper and the bell under it, so no pipe stays held."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False
        )
    else:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass


def _home(tmp_path: Path) -> dict[str, str]:
    (tmp_path / ".divineos-shared" / "letters").mkdir(parents=True)
    env = {**os.environ, "HOME": str(tmp_path)}
    env.pop("DOORBELL_ALLOW_UNTRACKED", None)
    return env


def _run(env: dict[str, str], out_path: Path | None, seconds: float = 5) -> tuple[int | None, str]:
    """Run the bell with stdout sent to out_path (a file), or to a pipe when out_path is None.

    Returns (exit code, or None if it was still listening when time ran out; what it printed).
    The trailing ':' keeps a bash parent alive so the bell's parent-gone guard does not fire.
    """
    # The wrapper prints the bell's own exit code, since the trailing ':' would otherwise make
    # the wrapper exit 0 whatever the bell did.
    if out_path == Path(os.devnull):
        # The shell `&` shape that failed: the bell's output goes to nowhere, the wrapper still talks.
        cmd = [
            BASH,
            "-c",
            f'bash "{BELL.as_posix()}" aether >/dev/null 2>&1; echo "bell-exit=$?"; :',
        ]
        out_path = None
    else:
        cmd = [BASH, "-c", f'bash "{BELL.as_posix()}" aether; echo "bell-exit=$?"; :']
    text = ""
    if out_path is None:
        # Popen, not run(): if the bell ARMS (a weakened check), it keeps the pipe open, and
        # run()'s timeout path then waits on the pipe forever and wedges the whole suite (Aria's
        # mutation of #699). The tree is killed on timeout so a weakened bell fails the assertion.
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=(os.name != "nt"),
        )
        try:
            text, _ = proc.communicate(timeout=seconds)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            text, _ = proc.communicate()
    else:
        with out_path.open("w", encoding="utf-8") as sink:
            try:
                subprocess.run(cmd, env=env, stdout=sink, stderr=sink, timeout=seconds)
            except subprocess.TimeoutExpired:
                pass
        text = out_path.read_text(encoding="utf-8", errors="replace")
    marker = "bell-exit="
    if marker not in text:
        return None, text
    return int(text.rsplit(marker, 1)[1].split()[0]), text


def test_a_bell_whose_output_goes_nowhere_refuses_to_arm(tmp_path):
    env = _home(tmp_path)
    code, out = _run(env, Path(os.devnull))
    assert code == 3, (code, out)
    assert not (tmp_path / ".divineos-shared" / ".aether_doorbell_alive").exists()


def test_a_bell_whose_output_is_a_pipe_refuses_to_arm(tmp_path):
    env = _home(tmp_path)
    code, out = _run(env, None)
    assert code == 3, (code, out)
    assert "DOORBELL NOT ARMED" in out and "run_in_background" in out


def test_a_bell_whose_output_is_a_background_task_file_arms(tmp_path):
    """The control: the refusals above are not just a bell that always refuses."""
    env = _home(tmp_path)
    task_dir = tmp_path / "claude" / "session" / "tasks"
    task_dir.mkdir(parents=True)
    code, out = _run(env, task_dir / "b123abc.output")
    assert code is None, (code, out)  # still listening when time ran out
    assert "doorbell armed" in out, out
    assert "override" not in out, out  # a watched bell does not claim an override


def test_the_override_arms_and_is_named_in_the_refusal(tmp_path):
    env = _home(tmp_path)
    env["DOORBELL_ALLOW_UNTRACKED"] = "1"
    code, out = _run(env, None)
    assert code is None and "doorbell armed" in out, (code, out)
    assert "override" in out, out  # Aria: an override that armed it must say so on the arming line
    env.pop("DOORBELL_ALLOW_UNTRACKED")
    _code, refusal = _run(env, None)
    assert "DOORBELL_ALLOW_UNTRACKED=1" in refusal
