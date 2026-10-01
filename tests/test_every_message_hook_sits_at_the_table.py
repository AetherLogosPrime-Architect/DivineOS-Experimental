"""Every per-message hook runs through Dad's table, so none can bypass it.

#560 folded the UserPromptSubmit list into dads_table.py. A hook added straight
into settings would run outside the table, beside it, where the table's order
and its single answer to him do not reach it -- and a merge that kept main's
settings entry would land it there silently (council-27845494f7d0, the leak its
game-walk left open). Only the question hold sits outside, on purpose: it must
refuse before the table runs at all.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ALLOWED_BESIDE_THE_TABLE = ("question_hold.py",)


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
        "these per-message hooks run outside Dad's table; add them to "
        f"dads_table_children.json instead: {beside}"
    )
