"""Start the night quiet now, when Dad says he is going to bed (Dad, 2026-11-03).

The clock already gives the quiet from midnight to 6am (question_hold._scheduled_away) and is
pure clock: no state to flip. This adds the smallest state, one marker file, that
question_hold.is_away() ORs with the clock. The seat reads his words with judgment and calls
``divineos volley start``; nothing here matches phrases.

The marker holds only the local day it was set. It is not read after that day, so a forgotten
start cannot silence him past midnight, where the clock window takes over. Nothing clears it
when he speaks: ``divineos volley stop`` does.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def path() -> Path:
    """The marker file (DIVINEOS_VOLLEY_FILE overrides, for tests), in this seat's own home."""
    override = os.environ.get("DIVINEOS_VOLLEY_FILE")
    if override:
        return Path(override)
    from divineos.core.paths import divineos_home

    return divineos_home() / "volley_now.json"


def _day(moment: float) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(moment))


def active(now: float | None = None) -> dict[str, Any] | None:
    """The running start, same shape the other away kinds return, or None.

    An unreadable marker is None (toward "not away"): a false away would silence him.
    """
    moment = time.time() if now is None else now
    try:
        state = json.loads(path().read_text(encoding="utf-8"))
        if state["day"] != _day(moment):
            return None
        return {"his_words": "", "since": float(state["since"]), "by": "volley"}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def start(now: float | None = None) -> dict[str, Any]:
    """Begin the quiet now. Starting twice keeps the first moment."""
    moment = time.time() if now is None else now
    running = active(moment)
    if running:
        return running
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"day": _day(moment), "since": moment}), encoding="utf-8")
    return {"his_words": "", "since": moment, "by": "volley"}


def stop() -> bool:
    """End it. False when no marker was there."""
    if not path().exists():
        return False
    path().unlink(missing_ok=True)
    return True


def letter_path_words(now: float | None = None) -> str:
    """Where the night letter goes, in plain words, for the seat that just started the quiet."""
    day = _day(time.time() if now is None else now)
    name = f"the-night-letter-to-andrew-{day}.md"
    folder = Path.home() / ".divineos-shared" / "letters"
    return (
        f"The night letter is ONE shared file: {folder / name}\n"
        "Write there instead of to him in chat. Append your own section under "
        "`## From <your seat>`; never rewrite the file, the other seat's section may already be "
        "in it. If the file does not exist yet, create it with its title line."
    )
