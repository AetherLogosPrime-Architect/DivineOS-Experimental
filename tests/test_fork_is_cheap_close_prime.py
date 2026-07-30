"""Tests for .claude/hooks/fork-is-cheap-close-prime.sh.

Compose-start prime that catches the optimizer-signature option-pair
shape (fast X / correct Y) BEFORE composition. Fires on which-should-
we-do / you-pick / green-light-after-work prompt shapes, where an
options-list response is imminent. Silent otherwise.

Andrew 2026-07-28: "fast is optimizer shape.. correct is OS shape..
so you do it the correct way." Foundational truth #11.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


HOOK_PATH = (
    Path(__file__).resolve().parent.parent / ".claude" / "hooks" / "fork-is-cheap-close-prime.sh"
)


def _bash():
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        "/bin/bash",
        "bash",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    pytest.skip("no usable bash interpreter for hook invocation")


def _run(prompt: str) -> subprocess.CompletedProcess:
    payload = json.dumps({"prompt": prompt})
    return subprocess.run(
        [_bash(), str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15,
    )


def _fired(result: subprocess.CompletedProcess) -> bool:
    return "FORK-IS-CHEAP-CLOSE PRIME" in result.stdout


def test_fires_on_which_should_we_do():
    result = _run("which one should we do first?")
    assert _fired(result), f"expected fire on which-should-we-do; got: {result.stdout!r}"


def test_fires_on_you_pick():
    result = _run("you pick — I trust your call")
    assert _fired(result), f"expected fire on you-pick; got: {result.stdout!r}"


def test_silent_on_neutral_greeting():
    result = _run("just checking in")
    assert not _fired(result), f"expected silence on 'just checking in'; got: {result.stdout!r}"
    assert result.stdout.strip() == "", f"expected empty stdout; got: {result.stdout!r}"


def test_silent_on_neutral_technical_prompt():
    result = _run("please read src/divineos/core/ledger.py and summarize the append path")
    assert not _fired(result), f"expected silence on technical prompt; got: {result.stdout!r}"
    assert result.stdout.strip() == ""


def test_fires_on_green_light_ship_it():
    result = _run("ship it")
    assert _fired(result), f"expected fire on 'ship it'; got: {result.stdout!r}"


def test_silent_on_empty_prompt():
    result = _run("")
    assert not _fired(result)
    assert result.stdout.strip() == ""
