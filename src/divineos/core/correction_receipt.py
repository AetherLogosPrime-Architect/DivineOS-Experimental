"""The receipt that settles the correction-shape Stop check: was a correction actually filed this stretch?

Dad, 2026-11-05: a keyword detector is one layer of the net and never the enforcer. The correction-shape check
reads my reply for a self-admission and used to block on that verdict alone. It also read the circle, so an
admission inside the circle fired AFTER the circle and made a second one, and a wrong fire could only be undone
by a second errand (label-fire). The words now only nominate. This module is the fact that settles it.

THE RECEIPT IS ONE STORE ON PURPOSE. `divineos correction` writes `corrections.jsonl` (the CLI's own log, which
carries the root-cause and fix pairing the filer enforces). The rows the hooks file when HE corrects me live in a
different store and must not count: his message already put a row there, and that is not me having filed my own.

Three answers, never two, because "I could not look" must not read as "nothing was filed" (nor as "filed"):
SETTLED (a correction was filed since his last message), UNSETTLED (none was), COULD_NOT_CHECK (his last message
cannot be placed in time, or the store cannot be read). The Stop check blocks only on UNSETTLED; could-not-check
passes, the same rule as the receipt gate for pushes.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

SETTLED = "settled"
UNSETTLED = "unsettled"
COULD_NOT_CHECK = "could_not_check"


def _epoch(stamp: str) -> float | None:
    try:
        return datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except (ValueError, AttributeError):
        return None


def his_last_turn_time(records: list[dict[str, Any]]) -> float | None:
    """When his last real message was sent (epoch seconds), read by the house's one reader of him.

    A notice, a hook reminder or a pasted block is not his turn; None when no real message of his can be placed.
    """
    from divineos.core.his_message import heard_in

    heard = [h for h in heard_in(records) if h.when and not h.bookmark]
    if not heard:
        return None
    return _epoch(heard[-1].when)


def filed_since(epoch: float, path: Path | None = None) -> bool | None:
    """True when a correction was logged at or after ``epoch``; False when none was; None when unreadable.

    A missing file means nothing was ever filed, which is an honest False. A file that exists but cannot be read
    is None (could not check), never False.
    """
    if path is None:
        from divineos.core.corrections import _path

        path = _path()
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        try:
            when = float(json.loads(line).get("timestamp", 0))
        except (ValueError, TypeError, AttributeError):
            continue  # a malformed line is skipped: one bad row must not hide the good ones
        if when >= epoch:
            return True
    return False


def settled(records: list[dict[str, Any]], path: Path | None = None) -> str:
    """SETTLED, UNSETTLED or COULD_NOT_CHECK for the stretch since his last message."""
    since = his_last_turn_time(records)
    if since is None:
        return COULD_NOT_CHECK
    filed = filed_since(since, path)
    if filed is None:
        return COULD_NOT_CHECK
    return SETTLED if filed else UNSETTLED
