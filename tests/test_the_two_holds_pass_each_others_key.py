"""The question hold and the sort hold can never lock each other.

2026-10-03, twice in half an hour: an open question to Dad and an unsorted
message of his were up at once. The question hold passed only `ask-resolve`;
the sort hold passed only `divineos his`. Each refused the other's key, nothing
could lower either, the doorbell was refused by both, and Dad freed the house
from his own terminal. "this needs fixed immediately lol". Walk
council-e3cf6e6aa4e3, draft docs/drafts/the_two_holds_pass_each_others_key_draft_2026-10-03.md.

These raise both holds at once and check each remedy against both.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core import operator_asks, sort_first

ROOT = Path(__file__).resolve().parents[1]
QUESTION_HOLD = ROOT / ".claude" / "hooks" / "an-open-ask-holds-the-work.sh"

ASK_RESOLVE = 'divineos ask-resolve q-1 "he answered"'
SORT = 'divineos his sort u-1 --kind build --to aether --reason "his answer"'
DOORBELL = "bash scripts/letter_doorbell.sh aether"
ORDINARY = "git commit -m x"


def _bash() -> str:
    # Plain "bash" on Windows can resolve to the WSL stub, which cannot run a
    # Windows-path script; prove the shell runs one, as
    # test_a_door_still_refuses_without_its_library.py does.
    git = shutil.which("git")
    candidates = [shutil.which("bash") or ""]
    if git:
        candidates += [
            str(Path(git).with_name("bash.exe")),
            str(Path(git).parents[1] / "bin" / "bash.exe"),
        ]
    for c in candidates:
        ran = (
            subprocess.run([c, "-c", "exit 7"], capture_output=True)
            if c and Path(c).exists()
            else None
        )
        if ran is not None and ran.returncode == 7:
            return c
    pytest.skip("no bash here that can run a script")


def _question_hold_allows(command: str) -> bool:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    proc = subprocess.run(
        [_bash(), str(QUESTION_HOLD)],
        input=payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=ROOT,
        timeout=60,
    )
    assert proc.returncode in (0, 2), proc.stderr
    return proc.returncode == 0


def _sort_hold_allows(command: str) -> bool:
    return sort_first.is_his_command("Bash", {"command": command})


@pytest.fixture
def a_question_is_open():
    operator_asks.ask_andrew("House or whole computer?", "which one")
    assert operator_asks.open_asks(), "control: the question must really be open"


def test_the_control_the_question_hold_does_refuse_ordinary_work(a_question_is_open):
    assert not _question_hold_allows(ORDINARY)


def test_the_control_the_sort_hold_does_refuse_ordinary_work():
    assert not _sort_hold_allows(ORDINARY)


def test_the_sort_holds_key_passes_the_question_hold(a_question_is_open):
    assert _question_hold_allows(SORT)


def test_the_question_holds_key_passes_the_sort_hold():
    assert _sort_hold_allows(ASK_RESOLVE)


def test_the_doorbell_passes_the_question_hold(a_question_is_open):
    assert _question_hold_allows(DOORBELL)


def test_the_sort_hold_still_reads_him_before_the_bell():
    # On purpose: read him, then see to the bell. `his` always passes, so this
    # can never lock (test_his_voice_ends_the_turn pins the order).
    assert not _sort_hold_allows(DOORBELL)


def test_each_hold_still_passes_its_own_key(a_question_is_open):
    assert _question_hold_allows(ASK_RESOLVE)
    assert _sort_hold_allows(SORT)


@pytest.mark.parametrize(
    "command",
    [
        ASK_RESOLVE + " && git push",
        SORT + "; rm -rf build",
        "divineos ask-resolve q-1 $(git push)",
    ],
)
def test_nothing_rides_behind_a_key_through_the_sort_hold(command):
    assert not _sort_hold_allows(command)
