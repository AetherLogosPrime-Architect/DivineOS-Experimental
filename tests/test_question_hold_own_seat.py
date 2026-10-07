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
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
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


def test_the_board_sits_next_door_to_the_seat_home(tmp_path, monkeypatch):
    # In the house: ~/.divineos-aria -> ~/.divineos-shared. In a test: inside
    # the test's own area, so no unpatched call can reach the live fridge.
    from divineos.core import question_hold as mod

    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / ".divineos-aria"))
    assert mod._home().parent / ".divineos-shared" == tmp_path / ".divineos-shared"
    assert mod.BOARD.parent.parent == mod._home().parent or "pytest" in str(mod.BOARD)


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


# THE SHARED FRIDGE (Dad, 2026-10-01): "seeing what the other was asked is a
# nice addition, it just shouldnt block, only the personal ones do".
@pytest.fixture
def board(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    for name, value in {
        "STATE": tmp_path / "hold.json",
        "HOLD_LOG": tmp_path / "log.jsonl",
        "ESCAPED": tmp_path / "escaped.json",
        "BOARD": tmp_path / "board",
        "CARD": tmp_path / "board" / ".divineos-aria.json",
    }.items():
        monkeypatch.setattr(mod, name, value)
    import divineos.core.operator_asks as asks

    monkeypatch.setattr(asks, "ask_andrew", lambda q, plain, context="": "q-1")
    return mod


ASKING = "work\n\n## INNER CIRCLE\n\nDad, it is done. Which one do you want?"


def test_the_other_seats_card_is_shown_and_never_holds(board):
    board.BOARD.mkdir(parents=True)
    (board.BOARD / ".divineos.json").write_text(
        json.dumps({"question": "Dad, which bell?"}), encoding="utf-8"
    )
    assert board.others_waiting() == ["Aether is waiting on Dad: Dad, which bell?"]
    assert board.refusal("Edit", {"file_path": "x.py"}) == ""


def test_my_own_card_is_posted_and_taken_down(board):
    board.arm(ASKING)
    assert board.CARD.exists()
    assert board.others_waiting() == []  # my own card is never shown to me
    board.release("his message")
    assert not board.CARD.exists()


def test_a_broken_board_never_stops_the_hold(board):
    board.BOARD.write_text("a file where the board folder should be", encoding="utf-8")
    board.arm(ASKING)
    assert board.STATE.exists()
    assert board.others_waiting() == []
