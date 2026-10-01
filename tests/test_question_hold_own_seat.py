"""A question holds only its own seat, and never a look or another gate's exit.

Aria, 2026-10-01 (walk-c9e9794e0f63). Aether's "Dad, should I turn my letter
doorbell back on?" held me, because both seats shared one note; and the hold
refused a look at the doorbell's output and `divineos prereg assess` while
the overdue gate refused the doorbell -- two gates holding each other's exit.
"""

from __future__ import annotations

import importlib
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


def test_each_seat_keeps_its_own_note(tmp_path, monkeypatch):
    seat_a = tmp_path / "a"
    seat_b = tmp_path / "b"
    import divineos.core.question_hold as mod

    monkeypatch.setenv("DIVINEOS_HOME", str(seat_a))
    a = importlib.reload(mod)
    a.STATE.parent.mkdir(parents=True, exist_ok=True)
    a.STATE.write_text(json.dumps({"question": "A asks?", "since": time.time()}), encoding="utf-8")
    assert a.STATE.parent == seat_a

    monkeypatch.setenv("DIVINEOS_HOME", str(seat_b))
    b = importlib.reload(mod)
    try:
        assert b.is_open() is None
        assert b.refusal("Edit", {"file_path": "x.py"}) == ""
    finally:
        monkeypatch.delenv("DIVINEOS_HOME")
        importlib.reload(mod)


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
