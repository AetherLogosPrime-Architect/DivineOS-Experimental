"""Was his last word to me spoken at a game table, or in the window?

Dad, 2026-10-28, at the first working Momir table: *"why do you keep leaving the table? speak in the
game chat like i have asked.. you are stalling the game.. im sitting there waiting for you to act only
to find you are speaking to me here"*, then *"ok then fix that so it doesnt happen when you are
playing games"*. The room gate held every reply where I used a tool and left no room, and at a game I
use tools on every turn, so it demanded a room in the window he had told me to stay out of.

What he wants is to be answered in the channel he last used. A live table is only my way of SEEING which
channel that was, so this answers the real question (walk-35612c61edd9, Hawking: the question as first
drafted, "is a game live", was not well formed) and is named for what it knows, not for Magic, so poker
or any later game needs no change (Dennett). It is one shared function so the other gates that pull me
into the window during a game can ask it too (Kahneman: fixing only the gate he named is the same
mistake as fixing only the door where a fault was first noticed).

Two facts, BOTH required:
  1. A table is live: a seat's bridge log under the table folder was written in the last two minutes.
     Every call at a live table writes to it and a table nobody plays at goes quiet.
  2. A line of his in the GAME chat is newer than his last message in the WINDOW. The seats record
     his game-chat lines in ``chat_seen_<seat>.txt`` when they show them to a seat, so that file's
     modified time is the last time he spoke at the table. If his window message is newer, he has
     switched channels and is talking to me here, so the answer is no (Penrose: the rule breaks at a
     channel switch).

Why two and not one: the first fact alone I can produce by calling the table myself, so it would be a
self-granted exemption. The second is an event only he can cause (Maturana and Varela: a self-audit is
not an external one). The residual is honest and stays named: anyone with a shell can forge both. This
is my own discipline aid and not a security wall.

Anything it cannot read means False, which means the gate asks exactly as it did before: could-not-look
never passes as he-is-at-a-table (Knuth).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

#: Where the table's logs live on this machine. ``MAGIC_RUN_DIR`` points a test (or another machine) at
#: a different folder; the default is where the table was built.
_DEFAULT_RUN_DIR = "C:/magic-play/run"

#: How long after the last call at the table it still counts as live.
LIVE_SECONDS = 120


def _run_dir() -> Path:
    return Path(os.environ.get("MAGIC_RUN_DIR") or _DEFAULT_RUN_DIR)


def _newest_mtime(folder: Path, pattern: str) -> float | None:
    times = [p.stat().st_mtime for p in folder.glob(pattern) if p.is_file()]
    return max(times) if times else None


def his_last_word_was_at_a_table(window_message_at: float | None) -> bool:
    """True when a table is live AND he spoke at it more recently than he spoke in the window.

    ``window_message_at`` is the time (epoch seconds) of his last message in the window. None, because it
    could not be read, means False: with no way to order his two voices the gate does not guess.
    """
    if window_message_at is None:
        return False
    try:
        folder = _run_dir()
        if not folder.is_dir():
            return False
        last_call = _newest_mtime(folder, "bridge_*.log")
        if last_call is None or time.time() - last_call > LIVE_SECONDS:
            return False
        last_game_line = _newest_mtime(folder, "chat_seen_*.txt")
        if last_game_line is None:
            return False
        return last_game_line > window_message_at
    except OSError:
        return False
