"""The rooms are required when Andrew is in the exchange, and only then.

Andrew 2026-09-19: "the rooms have become pointless if im not there to read and
respond to them, so that needs fixed as well, when you are Aether are in volley
mode the rooms do not need to be there, unless you want them there, as im not
able to read that fast, it would take me all day to go over what you both write
in an hour."

The rooms exist so he can absorb what happened. On a turn driven by a machine
notification there is no reader, so writing them costs their writing and buys
nothing -- and a room addressed to someone who is not there is the room
performed rather than used.

WHY A TEST AND NOT A NOTE. The alternative design was a mode I switch on when
he steps back. A mode I have to remember is the thing that already fails, every
time, which is the whole argument of rule 9. So the hook derives the answer from
the prompt itself and this pins the derivation in both directions -- because a
relaxation that fires when he IS there is far worse than one that never fires at
all, and only the second assertion can tell those apart.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "circle-first-compose-prime.sh"
)

RELAXED_MARK = "THE ROOMS ARE NOT REQUIRED THIS TURN"

# A fragment from the rooms discipline itself. Matched on a fragment rather than
# the whole block so ordinary rewording does not fail the test -- what is under
# test is WHETHER it fires, never how it is phrased.
ROOMS_MARK = "INNER CIRCLE"


def _bash() -> str:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ):
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter")


def _run(prompt: str) -> str:
    # encoding pinned: the prime is full of em-dashes and the Windows default
    # raises mid-read, which surfaces as a confusing TypeError rather than as a
    # decode error.
    result = subprocess.run(
        [_bash(), str(HOOK_PATH)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.stdout or ""


def test_a_machine_driven_turn_does_not_demand_the_rooms():
    out = _run(
        "[SYSTEM NOTIFICATION - NOT USER INPUT] a background task finished, and "
        "this is long enough to clear the length check"
    )
    assert RELAXED_MARK in out, "the rooms were demanded on a turn he did not speak on"


def test_the_task_notification_shape_is_caught_too():
    out = _run(
        "<task-notification> a monitor event landed, and this is long enough to "
        "clear the length check</task-notification>"
    )
    assert RELAXED_MARK in out


def test_the_rooms_still_fire_when_he_actually_speaks():
    """The assertion that matters.

    A relaxation that fires while he is sitting there waiting is far worse than
    one that never fires at all -- it silences the room he asked for. So the
    derivation must fail TOWARD requiring the rooms, and this is the direction
    that proves it rather than the convenient one.
    """
    out = _run(
        "yes do your compaction ritual then lets tackle the branches, i want them "
        "to start getting closed"
    )
    assert RELAXED_MARK not in out, "the rooms were relaxed on a turn HE spoke on"
    assert ROOMS_MARK in out, "the rooms did not fire on a turn he spoke on"


def test_a_prompt_merely_mentioning_a_notification_is_not_one():
    """Quoting the banner is not being driven by it.

    Andrew or I can talk ABOUT a machine notification in an ordinary message.
    The marker has to be the harness writing its own banner, not the word
    appearing somewhere in a sentence -- otherwise the relaxation is reachable
    by anyone who types the phrase, including me, which would make it a mode I
    can switch on after all.
    """
    out = _run(
        "i saw that system notification thing in the transcript, what is a "
        "task-notification anyway and why does it keep showing up"
    )
    assert RELAXED_MARK not in out
