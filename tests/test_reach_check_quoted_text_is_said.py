"""The reach-check doorman must read what a command RUNS, not what it SAYS.

2026-09-25: the correction-marker gate allowed only its remedies, and one
remedy took a --reason sentence mentioning a store-write verb. The doorman
matched the verb inside the quotes and refused the remedy, while the cure for
the doorman was refused by the marker. Neither door opened.

The same haystack also decided the remedy exemption, so a quoted mention of
`divineos reach` let a real write through. Both directions are pinned here.

The hook's python body is run directly with a stub reach_check that always
blocks, so exit 7 means "classified as a store-write". Going through bash would
let _lib.sh put the real src/ first on the path and query the real database.
"""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

from divineos.core.prior_art import REPO

HOOK = REPO / ".claude" / "hooks" / "reach-check-doorman.sh"

PRELUDE = """
import sys, types
import divineos.core
stub = types.ModuleType("divineos.core.reach_check")
stub.gate_status = lambda: (True, "STUB-BLOCK")
stub.satisfied_recently = lambda: (False, "")
sys.modules["divineos.core.reach_check"] = stub
divineos.core.reach_check = stub
"""


def _python_body() -> str:
    text = HOOK.read_text(encoding="utf-8")
    body = text[text.index("-c '") + len("-c '") :]
    return body[: body.index("\n' )")]


def _classified_as_write(command: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    result = subprocess.run(
        [sys.executable, "-c", PRELUDE + _python_body()],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode in (0, 7), result.stderr
    return result.returncode == 7


SAID_NOT_RUN = [
    # the 09-25 incident, same shape
    "python scripts/clear_correction_marker.py --cli-broken --reason "
    '"reach-check refused the remedy; log the lesson with divineos learn after"',
    "echo 'next I will divineos feel about it'",
    'git commit -m "note: divineos opinion wording"',
]

RUN = [
    # the control: a quoted body does not hide the verb in front of it
    'divineos learn "a quoted body is still a write"',
    "divineos feel -v 0.5 -a 0.3 -d 'x'",
    'cd x && divineos claim "y" --tier 3',
    # a quoted mention of the remedy must not buy an exemption
    'echo "divineos reach"; divineos learn "sneak"',
]


@pytest.mark.parametrize("command", SAID_NOT_RUN)
def test_a_quoted_mention_is_not_a_store_write(command):
    assert not _classified_as_write(command)


@pytest.mark.parametrize("command", RUN)
def test_a_real_store_write_is_still_seen(command):
    assert _classified_as_write(command)


def test_the_remedy_itself_still_passes():
    assert not _classified_as_write('divineos reach open "quoted text in gates"')
