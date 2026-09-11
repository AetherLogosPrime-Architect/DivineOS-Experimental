"""A header saying "this never blocks" is a test with no assertion.

Aria, 2026-09-10, after a comment in our own voice -- specific, sincere, and
wrong -- told her a refusal path was loud when it logged to nowhere. She
diagnosed the resulting incident twice by guessing, because the note had
answered the question she was about to ask. Her amendment: a note recording
the PAST cannot rot, but a note describing present behaviour is a promise the
note cannot keep, and the more it sounds like us the more completely it gets
believed.

So this is where that sentence lives now. The detector fires on every Bash
result in the session; if it ever gained a non-zero exit or a deny decision,
the freeze class it was written to avoid would come back silently while its
own header still said otherwise.

The pair is deliberate. The exit-zero assertion alone passes against a hook
that warns about nothing at all -- so one case proves it still fires, and the
other proves it is not merely always-on.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = (
    Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "ambiguous-verification-detector.sh"
)


# Bare "bash" on this box resolves to the WSL relay, which cannot reach
# /bin/bash and exits 1 without ever running the hook. That is COULD-NOT-LOOK,
# and the first draft of this file read it as "the advisory detector blocked" --
# a diagnostic accusing the subject of the exact defect the instrument had
# failed to measure. Three-valued or nothing: found, found-nothing,
# could-not-look, and the third must never wear the coat of either other.
def _bash() -> str | None:
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()

needs_hook = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)

# The shape the detector exists for: a check whose exit status IS the answer,
# piped into something that discards it.
MASKED = "bash scripts/check_push_readiness.sh | tail -5"


def _run(command: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run(
        [str(BASH), str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    if "execvpe" in result.stderr or "cannot execute" in result.stderr:
        pytest.skip(f"bash never ran the hook -- could-not-look: {result.stderr.strip()!r}")
    # The hook speaks on STDERR -- that is the stream Claude Code surfaces for
    # a PostToolUse advisory. Asserting on stdout alone read its warnings as
    # silence, which is the same one-pipe blindness the detector itself exists
    # to catch, committed inside its own test.
    result.said = result.stdout + result.stderr  # type: ignore[attr-defined]
    return result


@needs_hook
def test_it_still_fires_on_the_shape_it_was_built_for():
    """The red half. Without it the advisory assertions below are vacuous."""
    result = _run(MASKED)

    assert "EXIT STATUS IS THE PIPE'S" in result.said, (
        "the detector stopped detecting the pipeline-masking shape it exists for; "
        f"it said {result.said!r}"
    )


@needs_hook
def test_firing_costs_a_glance_and_never_a_turn():
    """The claim its own header makes, now with something behind it."""
    result = _run(MASKED)

    assert result.returncode == 0, (
        "the advisory detector blocked. Its header promises a wrong warning costs "
        f"a glance, not a turn; exit was {result.returncode}"
    )
    assert "permissionDecision" not in result.said, (
        "the advisory detector emitted a permission decision. Advisory means the "
        "turn continues whether or not the warning was right."
    )


@needs_hook
def test_it_covers_the_incident_named_in_its_own_header():
    """The push-readiness script piped into tail IS this detector's origin
    story, and for three weeks the detector could not see it -- the first-stage
    list held the commands that had burned me rather than the category they
    belong to. A script called check_* or verify_* says in its own name that
    its exit status is the answer."""
    for probe in (
        "bash scripts/check_push_readiness.sh | tail -5",
        "python scripts/verify_push_landed.py | head -3",
    ):
        assert "EXIT STATUS IS THE PIPE'S" in _run(probe).said, (
            f"a verification script's verdict was masked and nothing said so: {probe}"
        )


@needs_hook
def test_pipefail_is_still_treated_as_handled():
    """The escape has to keep working, or the detector punishes the remedy it
    prescribes and gets routed around."""
    result = _run("bash scripts/check_push_readiness.sh 2>&1 | tail -5; set -o pipefail")

    assert "EXIT STATUS IS THE PIPE'S" not in result.said, (
        "it warned at a command that had already handled the masking"
    )


@needs_hook
def test_a_benign_command_draws_no_warning():
    """Control. An always-on warning is furniture, and furniture passing the
    assertions above would make them look like coverage."""
    result = _run("echo hello")

    assert result.returncode == 0
    assert result.said.strip() == "", (
        f"it warned about a command carrying none of its shapes: {result.said!r}"
    )
