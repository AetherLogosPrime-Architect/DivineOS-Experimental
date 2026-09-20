"""Registered is not the same as live, and live is not the same as arriving.

2026-09-20: the UserPromptSubmit context hook was correctly registered, its
composing function was correctly imported, and for an unknown stretch of turns
it delivered nothing at all. A block added to the composition re-embedded the
whole substrate through a freshly loaded transformer on every prompt, so the
hook ran past the harness budget and was killed. It is fail-open by design and
sends its own stderr nowhere, so a killed hook and a hook with nothing to say
emit byte-identical silence. Measured at the time: zero bytes, still running at
110 seconds. Unwired: about one second.

The sibling test in test_a_wrapped_hook_is_not_a_dark_hook pins the REGISTER —
that the hook which actually runs is the one recorded as wired. This pins the
next question down, which that one cannot see: a hook can be perfectly
registered and still deliver nothing.

WHY THIS ASSERTS TIME AND NOT CONTENT, which is a limit rather than an
oversight. Under the suite's fixtures the data home is a temporary directory,
so the composition has genuinely nothing to say and emitting nothing is the
correct answer. An assertion on content could not tell that apart from the
outage — which is the very confusion this file exists about, so writing it
would have reproduced the fault inside the instrument. What DID regress is
bounded runtime, and that is assertable here honestly.

WHY A UNIT TEST OF THE COMPOSING FUNCTION WOULD NOT HAVE CAUGHT IT. The suite
did call that function, in nine tests, and those tests died — but they died as
xdist worker crashes with no traceback, because the per-test time limit kills
the process on this platform. Reading them as slow-or-flaky is the obvious
reading and it costs hours.

The budget is set an order of magnitude above the observed cost so that only a
structural regression trips it: a new heavy surface on the composition path, or
a lane re-wired to something that loads a model.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK = REPO_ROOT / ".claude" / "hooks" / "pre-response-context.sh"

# Observed at about one second with the composition healthy. Ten seconds is a
# regression detector, not a performance target: anything that pushes an
# ordinary compose past this is doing work that does not belong on the path
# that runs before every single turn.
BUDGET_SECONDS = 10.0

# The run is abandoned well before the suite's own per-test limit, so a hung
# hook produces an ordinary assertion naming the hook rather than a killed
# worker with no traceback — which is the unreadable failure this whole file
# exists to replace.
KILL_AFTER_SECONDS = BUDGET_SECONDS * 1.5

PAYLOAD = json.dumps(
    {
        "prompt": "a prompt of ordinary length, long enough to be surfaced on",
        "transcript_path": "",
    }
)


def _working_bash() -> str | None:
    """Return a bash that can actually run a script, or None.

    THE CONTROL IS ASSERTED LIVE, and the first version of this file did not do
    that. ``shutil.which("bash")`` on this box resolves to the WSL relay, which
    is present, is executable, and cannot run a Windows-path script — it failed
    with a missing-interpreter error from inside a different filesystem. A name
    that resolves is not an object that works, so each candidate is made to
    prove itself by running something trivial before it is trusted.
    """
    candidates = []
    git = shutil.which("git")
    if git:
        # Git for Windows ships bash beside git in the same bin directory.
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
                [candidate, "-c", "echo ok"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()

requires_hook = pytest.mark.skipif(
    not HOOK.exists(), reason="context hook absent from this checkout"
)
requires_bash = pytest.mark.skipif(BASH is None, reason="no working bash on this platform")


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the hook and everything it started.

    The hook spawns a Python child, so killing only the shell leaves the real
    worker running — and on Windows that orphan is what holds the output handle
    open.
    """
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
            capture_output=True,
            check=False,
        )
    try:
        proc.kill()
    except OSError:
        pass


def _run_hook() -> tuple[int | None, str, float]:
    """Run the hook, returning (returncode, output, elapsed). None means hung.

    OUTPUT GOES TO A FILE RATHER THAN A PIPE, and this was found by running the
    control rather than by reasoning about it. With a pipe, a timeout raises
    and then blocks forever joining the reader thread, because a descendant
    still holds the write handle — so the test hung past its own deadline and
    died as a killed worker anyway, reproducing the exact failure it exists to
    replace. A file has no reader thread to join.
    """
    assert BASH is not None
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace") as sink:
        started = time.monotonic()
        proc = subprocess.Popen(
            [BASH, str(HOOK)],
            stdin=subprocess.PIPE,
            stdout=sink,
            stderr=subprocess.DEVNULL,
            cwd=str(REPO_ROOT),
            text=True,
        )
        try:
            if proc.stdin is not None:
                proc.stdin.write(PAYLOAD)
                proc.stdin.close()
            try:
                returncode: int | None = proc.wait(timeout=KILL_AFTER_SECONDS)
            except subprocess.TimeoutExpired:
                _kill_tree(proc)
                returncode = None
        finally:
            if proc.poll() is None:
                _kill_tree(proc)
        elapsed = time.monotonic() - started
        sink.seek(0)
        return returncode, sink.read(), elapsed


@requires_hook
@requires_bash
def test_the_context_hook_returns_within_budget() -> None:
    """The hook must finish long before anything would kill it.

    This is the half that actually regressed. The outage was not an error —
    the composition simply never returned, and a fail-open hook reports that
    as silence.
    """
    returncode, _out, elapsed = _run_hook()

    assert returncode is not None, (
        f"the context hook did not return within {KILL_AFTER_SECONDS}s and was killed. "
        "In live use this is invisible: the hook is fail-open, so a hang and a "
        "quiet turn deliver the same nothing. Look for work added to "
        "build_combined_context that loads a model or runs unbounded."
    )
    assert returncode == 0, f"the hook exited {returncode}"
    assert elapsed < BUDGET_SECONDS, (
        f"the context hook took {elapsed:.1f}s against a {BUDGET_SECONDS}s budget. "
        "It has not failed yet, and this is the state immediately before it "
        "starts being killed and reporting that as silence."
    )


@requires_hook
@requires_bash
def test_whatever_the_hook_emits_is_the_shape_the_harness_reads() -> None:
    """Bytes in the wrong shape are also silence.

    Emptiness is allowed here and only here: with a temporary data home there
    may be nothing to surface. What is not allowed is output the harness cannot
    read, which would deliver nothing while looking like delivery.
    """
    returncode, out, _elapsed = _run_hook()
    assert returncode is not None, "the hook hung — see the budget test for what that means"
    if not out.strip():
        pytest.skip("nothing surfaced from this fixture's data home, which is a valid state")
    payload = json.loads(out)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context.strip(), "the field the harness actually reads came back empty"
