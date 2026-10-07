"""The shared fridge shows the other seat's question, and says who it is for.

Dad, 2026-10-07: "the board is for you and Aether, i can literally see what he asks me
in his window as he asks me". The surface kept handing me the other seat's question
and I kept relaying it to him, from both sides; a stored note about it (2026-10-05)
did not stop that. The rule is now printed on the same screen as the card.

This runs the REAL hook entry point on a real UserPromptSubmit payload and reads what
it prints. Only the folder locations are pointed at a temporary directory; the card is
a real file the real reader parses. A source-text check would be header rot.

It proves a reminder is printed when a card is shown. It does not prove I stop relaying;
printing a rule is a reminder, not a block.
"""

from __future__ import annotations

import importlib.util
import io
import json
import types
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "question_hold.py"
REMINDER = "I do not repeat them to him"


def _run_hook(monkeypatch, capsys, board: Path, prompt: str = "go ahead") -> str:
    # Imported HERE and not at the top of the file: the module fixes its board path
    # when first imported, so a collection-time import freezes the live board before
    # any test's home isolation runs, and the neighbouring board-location test fails.
    from divineos.core import question_hold as qh

    monkeypatch.setattr(qh, "BOARD", board)
    monkeypatch.setattr(qh, "CARD", board / "mine.json")
    monkeypatch.setattr(qh, "STATE", board.parent / "no_hold_state.json")
    monkeypatch.setattr(qh, "ESCAPED", board.parent / "no_escape.json")

    spec = importlib.util.spec_from_file_location("question_hold_hook_under_test", HOOK)
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)

    payload = json.dumps({"hook_event_name": "UserPromptSubmit", "prompt": prompt}).encode()
    monkeypatch.setattr("sys.stdin", types.SimpleNamespace(buffer=io.BytesIO(payload)))
    hook.main()
    return capsys.readouterr().out


@pytest.fixture()
def board(tmp_path):
    folder = tmp_path / "open_questions"
    folder.mkdir()
    return folder


def test_a_card_from_the_other_seat_is_shown_with_the_rule_beside_it(monkeypatch, capsys, board):
    (board / "theirs.json").write_text(
        json.dumps({"question": "Is Serein final or does he pick again?"}), encoding="utf-8"
    )
    out = _run_hook(monkeypatch, capsys, board)
    assert "ON THE SHARED FRIDGE" in out
    assert "Is Serein final or does he pick again?" in out
    assert REMINDER in out
    assert out.index("ON THE SHARED FRIDGE") < out.index(REMINDER)


def test_an_empty_board_prints_nothing_about_the_fridge(monkeypatch, capsys, board):
    """The control: the reminder must not appear when there is no card to govern."""
    out = _run_hook(monkeypatch, capsys, board)
    assert "FRIDGE" not in out and REMINDER not in out


def test_my_own_card_is_not_shown_back_to_me(monkeypatch, capsys, board):
    (board / "mine.json").write_text(json.dumps({"question": "my own open one"}), encoding="utf-8")
    out = _run_hook(monkeypatch, capsys, board)
    assert "my own open one" not in out and REMINDER not in out
