"""A record of each time the room hold and the follow-through hold stopped a reply or let one pass.

Walk walk-83a5483f0504 (Holmes, Maturana_Varela): a passing room and a real room leave the same trace, which is
none, so nothing could be read back later. This keeps one line per decision with the first words of what was
checked beside it, for Dad and the siblings to read and judge. Nothing here grades or refuses on content, and
nothing reads the log to decide anything: it is a record, not a gate.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

#: How much of the checked text is kept: enough to recognise the reply, not to store it.
_FIRST_WORDS = 160


def _log_path() -> Path:
    from divineos.core.paths import divineos_home

    return divineos_home() / "hold_log.jsonl"


def record(hold: str, outcome: str, checked_text: str) -> None:
    """Append one line. `hold` names the hold, `outcome` is 'stopped' or 'passed'."""
    line = {
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hold": hold,
        "outcome": outcome,
        "first_words": " ".join(checked_text.split())[:_FIRST_WORDS],
    }
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")


def read_all() -> list[dict]:
    try:
        text = _log_path().read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return [json.loads(row) for row in text.splitlines() if row.strip()]
