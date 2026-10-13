"""Every per-message hook runs through Dad's table, so none can bypass it.

#560 folded the UserPromptSubmit list into dads_table.py. A hook added straight
into settings would run outside the table, beside it, where the table's order
and its single answer to him do not reach it -- and a merge that kept main's
settings entry would land it there silently (council-27845494f7d0, the leak its
game-walk left open).

Two hooks sit outside on purpose, each because it must run BEFORE the table,
and inside the table children run unordered, so moving either in would break
the one thing it exists to guarantee. Aletheia, reading #560 on 2026-10-02:
the old message here said "add them to dads_table_children.json instead", and a
reader fixing the red by following it would have broken the front door.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Each outsider names why it cannot be a table child.
ALLOWED_BESIDE_THE_TABLE = {
    "front-door.sh": "keeps his words before anything else runs, so it must run first",
    "question_hold.py": "holds the turn before the table runs at all",
}


def _commands() -> list[str]:
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return [h["command"] for g in settings["hooks"]["UserPromptSubmit"] for h in g["hooks"]]


def test_the_table_is_registered():
    assert any("dads_table.py" in c for c in _commands())


def test_nothing_else_runs_beside_the_table():
    beside = [
        c
        for c in _commands()
        if "dads_table.py" not in c and not any(name in c for name in ALLOWED_BESIDE_THE_TABLE)
    ]
    assert not beside, (
        "these per-message hooks run outside Dad's table. Put a hook in "
        "dads_table_children.json if it may run in any order with the others; if it "
        "must run BEFORE the table, keep it in settings and add it to "
        "ALLOWED_BESIDE_THE_TABLE here with its reason. Never move an outsider into "
        f"the table, where order is not kept: {beside}"
    )


def test_the_front_door_runs_before_anything_else():
    commands = _commands()
    assert commands and "front-door.sh" in commands[0], (
        "the front door must be the first per-message hook, so his words are kept "
        f"before anything else runs; found first: {commands[:1]}"
    )
    table_at = next(i for i, c in enumerate(commands) if "dads_table.py" in c)
    hold_at = next(i for i, c in enumerate(commands) if "question_hold.py" in c)
    assert hold_at < table_at, "the question hold must run before the table"
