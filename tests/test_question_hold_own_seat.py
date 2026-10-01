"""A question holds only its own seat, and never a look or another gate's exit.

Aria, 2026-10-01 (walk-c9e9794e0f63). Aether's "Dad, should I turn my letter
doorbell back on?" held me, because both seats shared one note; and the hold
refused a look at the doorbell's output and `divineos prereg assess` while
the overdue gate refused the doorbell -- two gates holding each other's exit.
"""

from __future__ import annotations

import json
import time

import pytest


@pytest.fixture
def armed(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    mod.STATE.write_text(
        json.dumps({"question": "Dad, which one?", "ask_id": "q-1", "since": time.time()}),
        encoding="utf-8",
    )
    return mod


def test_each_seat_resolves_its_own_home(tmp_path, monkeypatch):
    # WRITES NOTHING, on purpose. The first version reloaded the module and
    # wrote a fake question; under the pre-push run its "temporary" home was a
    # live one, and "A asks?" held both seats until Dad spoke (2026-10-01).
    # The property is where each seat's note would live, so ask only that.
    from divineos.core import question_hold as mod

    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "a"))
    seat_a = mod._home()
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "b"))
    seat_b = mod._home()
    assert seat_a == tmp_path / "a"
    assert seat_b == tmp_path / "b"


def test_the_note_is_not_written_to_the_shared_home():
    # The defect itself, pinned: one Path.home() file shared by every seat.
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "src/divineos/core/question_hold.py").read_text(
        encoding="utf-8"
    )
    assert 'Path.home() / ".divineos"' not in src


@pytest.mark.parametrize(
    "command",
    [
        # Exactly as held on 2026-10-01.
        'cat "C:/Users/aethe/AppData/Local/Temp/claude/x/tasks/bxkhn42id.output"',
        'divineos prereg assess prereg-6766810e0572 --outcome DEFERRED --actor aria --notes "not measured"',
        "divineos prereg show prereg-6766810e0572",
        "grep -n x README.md",
    ],
)
def test_a_look_or_another_gates_exit_passes(armed, command):
    assert armed.refusal("Bash", {"command": command}) == ""


@pytest.mark.parametrize(
    "command",
    ["git commit -m x", "rm -rf build", "grep x a > out.txt", "python -c 'print(1)'"],
)
def test_building_still_waits(armed, command):
    assert "QUESTION HOLD" in armed.refusal("Bash", {"command": command})


def test_an_edit_still_waits_and_says_when_it_was_asked(armed):
    why = armed.refusal("Edit", {"file_path": "src/x.py"})
    assert "QUESTION HOLD" in why
    assert "asked 20" in why
