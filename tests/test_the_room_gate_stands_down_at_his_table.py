"""The room gate says nothing while a game table is live, whichever window Dad typed in.

Dad, at the first working Momir table, 2026-10-28: "why do you keep leaving the table? speak in the
game chat like i have asked.. you are stalling the game", then "ok then fix that so it doesnt happen
when you are playing games". The room gate held every reply where I used a tool and left no room, and
at a game I use tools every turn, so it demanded a room in the window he had told me to stay out of.

THE FIRST VERSION OF THIS FIX WAS WRONG, AND HE SHOWED IT WITHIN THE HOUR. It stood down only when a line
of his in the game chat was newer than his last message in the window, so the gate asked again the
moment he wrote here (the council walk's Penrose lens, walk-35612c61edd9). He then wrote "ok go sit back
down at the table" IN THE WINDOW, the gate asked, I answered him in the window twice, and he said "you
are demonstrably not back at the table". His rule is that during a game I answer him at the table,
whichever window he typed in. So the test that pinned the wrong behaviour is replaced by one that pins
the exact case that failed.

What each test pins:
- the gate still fires with no table at all (the control: the instrument can find its case);
- it stays silent while a seat has called the table in the last two minutes, EVEN WHEN he has just
  written in the window (tonight's failure);
- a table gone quiet, or a missing folder, means it asks as it always did (Knuth: could-not-look
  never passes as a-table-is-live);
- a stand-down is written to the hold log, so a quiet gate shows as a count (Norman).
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
    return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}}


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}


def _worked(window_at):
    """He spoke in the window at `window_at`, I used a tool, and the reply carries no room."""
    return [_user("go sit back down at the table", window_at), _tool(), _tool_result(), _said("Done.")]


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


def test_a_live_table_silences_the_gate(table):
    _touch(table / "bridge_Aria.log", NOW - 10)  # a seat called the table 10 seconds ago
    assert room.verdict(_worked(NOW - 600)) is None


def test_it_stays_silent_even_when_he_has_just_written_in_the_window(table):
    # TONIGHT'S FAILURE, pinned. He wrote in the window 20 seconds ago, a table is live, and the first
    # version of this fix asked for a room here, so I answered him in the window and left the table.
    _touch(table / "bridge_Aria.log", NOW - 10)
    _touch(table / "chat_seen_aria.txt", NOW - 600)  # his last game-chat line was long ago: it no longer matters
    assert room.verdict(_worked(NOW - 20)) is None


def test_a_table_gone_quiet_does_not_hold_the_gate_down(table):
    _touch(table / "bridge_Aria.log", NOW - 130)  # nobody has called the table for over two minutes
    assert room.verdict(_worked(NOW - 300))


def test_a_table_inside_the_two_minutes_still_counts(table):
    _touch(table / "bridge_Aether.log", NOW - 110)  # the other seat's log counts too: it is one table
    assert room.verdict(_worked(NOW - 300)) is None


def test_an_empty_fresh_log_counts_as_a_table_that_just_started(table):
    path = table / "bridge_Aria.log"
    path.write_text("", encoding="utf-8")
    os.utime(path, (NOW - 5, NOW - 5))
    assert room.verdict(_worked(NOW - 300)) is None


def test_a_missing_folder_means_the_gate_asks_as_it_always_did(tmp_path, monkeypatch):
    monkeypatch.setenv("MAGIC_RUN_DIR", str(tmp_path / "no_such_folder"))
    monkeypatch.setattr(time, "time", lambda: NOW)
    assert room.verdict(_worked(NOW - 300))


def test_a_folder_with_no_bridge_logs_means_the_gate_asks(table):
    _touch(table / "chat_seen_aria.txt", NOW - 5)  # his lines alone do not make a table
    assert room.verdict(_worked(NOW - 300))


def test_a_stand_down_is_recorded_so_a_quiet_gate_is_visible(table, monkeypatch):
    _touch(table / "bridge_Aria.log", NOW - 10)
    seen = []
    import divineos.core.hold_log as hold_log

    monkeypatch.setattr(hold_log, "record", lambda hold, outcome, text: seen.append((hold, outcome)))
    assert room.verdict(_worked(NOW - 300)) is None
    assert ("room", "stood_down") in seen
