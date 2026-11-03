"""When the room gate cannot read his last message it asks AND says so in the hold log.

Second-reader finding on #745: the gate wrote an `away_unreadable` row only when the away reading
RAISED. The other way of not being able to look, his message simply could not be read (no store, a
read error, nothing real in it), returned an empty reading and the gate asked in silence, so a
broken store at night looked identical to a quiet, healthy evening. A gate that falls back to asking
must show the fall as a count. Real store paths, nothing in the reading is patched.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import time
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
_spec = importlib.util.spec_from_file_location("dads_room_stop_unreadable", HOOK)
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)


def _worked_no_room():
    return [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "ok"}],
            },
        },
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}},
    ]


def _room_rows():
    from divineos.core import hold_log

    return [r for r in hold_log.read_all() if r["hold"] == "room"]


def test_an_unreadable_last_message_asks_and_is_logged():
    """THE DEFECT: with no readable message the gate asked and left no trace of why.
    (The conftest points his store at a file that does not exist, a real could-not-look.)"""
    assert room.verdict(_worked_no_room())
    rows = _room_rows()
    assert any(r["outcome"] == "away_unreadable" for r in rows), rows
    unreadable = [r for r in rows if r["outcome"] == "away_unreadable"][-1]
    assert "could not be read" in unreadable["first_words"]


def test_a_readable_last_message_leaves_no_unreadable_row(tmp_path, monkeypatch):
    """CONTROL: a store that reads fine must not be reported as unreadable."""
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    conn.execute("INSERT INTO messages VALUES (?, ?)", ("go", time.time() - 30))
    conn.commit()
    conn.close()
    assert room.verdict(_worked_no_room())
    assert not [r for r in _room_rows() if r["outcome"] == "away_unreadable"]
