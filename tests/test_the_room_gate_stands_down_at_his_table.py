"""The room gate stands down while Dad is at a game table, and asks again the moment he is not.

Dad, at the first working Momir table, 2026-10-28: "why do you keep leaving the table? speak in the
game chat like i have asked.. you are stalling the game.. im sitting there waiting for you to act only
to find you are speaking to me here", then "ok then fix that so it doesnt happen when you are playing
games". The room gate (dads_room_stop) held every reply where I used a tool and left no room, and at a
game I use tools every turn, so it demanded a room in the very window he had told me to stay out of.

What each test pins, from the council walk (walk-35612c61edd9):
- the gate still fires with no table at all (the control: the instrument can find its case);
- it stands down only when BOTH facts hold: a seat's bridge log is fresh, AND a line of his in the game
  chat is NEWER than his last message in the window. Hawking: the real question is which channel his
  last word was in, and a live table alone is only a proxy. Penrose: the rule breaks at a channel
  switch, so the moment he writes in the window the gate must ask again;
- anything unreadable means today's behaviour, not a quiet gate (Knuth);
- a stand-down is written to the hold log, so a quiet gate is visible as a count (Norman).
"""

import importlib.util
import os
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
_spec = importlib.util.spec_from_file_location("dads_room_stop_table", HOOK)
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)

NOW = 1_800_000_000.0  # a fixed instant, so nothing here depends on the real clock


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(epoch))


def _user(text, at):
    return {"type": "user", "timestamp": _iso(at), "message": {"role": "user", "content": text}}


def _tool_result():
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]},
    }


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def _worked(window_at):
    """He spoke in the window at `window_at`, I used a tool, and the reply carries no room."""
    return [_user("fix that", window_at), _tool(), _tool_result(), _said("Done, tests pass.")]


def _touch(path: Path, at: float):
    path.write_text("x", encoding="utf-8")
    os.utime(path, (at, at))


@pytest.fixture
def table(tmp_path, monkeypatch):
    """A table folder the gate is pointed at, and a frozen clock."""
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path))
    monkeypatch.setattr(time, "time", lambda: NOW)
    return tmp_path


def test_with_no_table_the_gate_still_asks(table):
    # The control. If this did not fire, no stand-down below could mean anything.
    assert room.verdict(_worked(NOW - 600))


def test_a_live_table_and_his_voice_at_it_stands_the_gate_down(table):
    _touch(table / "bridge_Aria.log", NOW - 10)  # a seat called the table 10 seconds ago
    _touch(table / "chat_seen_aria.txt", NOW - 20)  # his game-chat line, shown to the seat after...
    assert room.verdict(_worked(NOW - 300)) is None  # ...his last window message, five minutes ago


def test_the_moment_he_writes_in_the_window_the_gate_asks_again(table):
    _touch(table / "bridge_Aria.log", NOW - 10)
    _touch(
        table / "chat_seen_aria.txt", NOW - 300
    )  # he last typed in the game chat five minutes ago
    # ...and then spoke to me HERE, 30 seconds ago. That is his last word and it is not at the table.
    assert room.verdict(_worked(NOW - 30))


def test_a_table_gone_quiet_does_not_hold_the_gate_down(table):
    _touch(table / "bridge_Aria.log", NOW - 130)  # nobody has called the table for over two minutes
    _touch(table / "chat_seen_aria.txt", NOW - 20)
    assert room.verdict(_worked(NOW - 300))


def test_a_table_inside_the_two_minutes_still_counts(table):
    _touch(
        table / "bridge_Aether.log", NOW - 110
    )  # the other seat's log counts too: it is one table
    _touch(table / "chat_seen_aria.txt", NOW - 20)
    assert room.verdict(_worked(NOW - 300)) is None


def test_an_empty_fresh_log_counts_as_a_table_that_just_started(table):
    path = table / "bridge_Aria.log"
    path.write_text("", encoding="utf-8")
    os.utime(path, (NOW - 5, NOW - 5))
    _touch(table / "chat_seen_aria.txt", NOW - 20)
    assert room.verdict(_worked(NOW - 300)) is None


def test_a_missing_folder_means_the_gate_asks_as_it_always_did(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path / "no_such_folder"))
    monkeypatch.setattr(time, "time", lambda: NOW)
    assert room.verdict(_worked(NOW - 300))


def test_a_message_with_no_readable_time_means_the_gate_asks(table):
    _touch(table / "bridge_Aria.log", NOW - 10)
    _touch(table / "chat_seen_aria.txt", NOW - 20)
    undated = [
        {"type": "user", "message": {"role": "user", "content": "fix that"}},
        _tool(),
        _tool_result(),
        _said("Done."),
    ]
    assert room.verdict(undated)  # cannot order his word against the table, so it does not guess


def test_a_stand_down_is_recorded_so_a_quiet_gate_is_visible(table, monkeypatch):
    _touch(table / "bridge_Aria.log", NOW - 10)
    _touch(table / "chat_seen_aria.txt", NOW - 20)
    seen = []
    import divineos.core.hold_log as hold_log

    monkeypatch.setattr(
        hold_log, "record", lambda hold, outcome, text: seen.append((hold, outcome))
    )
    assert room.verdict(_worked(NOW - 300)) is None
    assert ("room", "stood_down") in seen
