"""Was his last word to me spoken at a game table, or in the window?

Dad, 2026-10-28, at the first working Momir table: *"why do you keep leaving the table? speak in the
game chat like i have asked.. you are stalling the game.. im sitting there waiting for you to act only
to find you are speaking to me here"*, then *"ok then fix that so it doesnt happen when you are
playing games"*. The room gate held every reply where I used a tool and left no room, and at a game I
use tools on every turn, so it demanded a room in the window he had told me to stay out of.

One fact: a table is live, meaning a seat's bridge log under the table folder was written in the last two
minutes. Every call at a live table writes to it and a table nobody plays at goes quiet. It is named for
what it knows, not for Magic, so poker or any later game needs no change (Dennett), and it is one shared
function so the other gates that pull me into the window during a game can ask it too (Kahneman: fixing
only the gate he named is the same mistake as fixing only the door where a fault was first noticed).

THE FIRST VERSION WAS WRONG AND DAD SHOWED IT WITHIN THE HOUR. It also required a line of his in the game
chat to be newer than his last message in the window, so that the gate asked again the moment he wrote
here (Penrose, walk-35612c61edd9: the rule breaks at a channel switch). He wrote "ok go sit back down at
the table" in the window, the gate asked for a room, I answered him in the window, and he said "you are
demonstrably not back at the table". His rule is that during a game I answer him at the table, whichever
window he typed in. My walk's cleverness was outranking his words, so the channel-order test is gone.

Residual, named: the one fact is something I could produce by calling the table myself (Maturana and
Varela: a self-audit is not an external one). It is logged on every stand-down, and this is my own
discipline aid and not a security wall.

Anything it cannot read means False, which means the gate asks exactly as it did before: could-not-look
never passes as a-table-is-live (Knuth).
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

#: How long a PAUSED file still counts. Six hours: a pause to read cards, never a night.
PAUSE_SECONDS = 6 * 3600


def _run_dir() -> Path:
    return Path(os.environ.get("MAGIC_RUN_DIR") or _DEFAULT_RUN_DIR)


def _newest_mtime(folder: Path, pattern: str) -> float | None:
    times = [p.stat().st_mtime for p in folder.glob(pattern) if p.is_file()]
    return max(times) if times else None


#: Where the poker table answers. ``POKER_TABLE_URL`` points a test at a stand-in server.
_DEFAULT_POKER_URL = "http://127.0.0.1:8765"


def _poker_table_is_live() -> bool:
    """A hand is live or the next deal is counting down, and Dad has not ended the game.

    Asked of the table itself, the same fact the poker stop hook reads. Could-not-look is False, so a
    table that is down never passes as a live one (Knuth).
    """
    import json
    import urllib.request

    url = (os.environ.get("POKER_TABLE_URL") or _DEFAULT_POKER_URL).rstrip("/")
    try:
        with urllib.request.urlopen(f"{url}/state?seat=aria", timeout=1.0) as reply:
            view = json.load(reply)
    except (OSError, ValueError):
        return False
    if not isinstance(view, dict) or view.get("hand") is None or view.get("released"):
        return False
    return bool(view.get("live")) or view.get("deal_in") is not None


def a_game_table_is_live() -> bool:
    """True when a seat has called the table within the last two minutes.

    REVISED the same night it was built. The first version also required a line of his in the game
    chat to be newer than his last message in the window (so the gate asked again the moment he wrote
    here). Dad showed that was wrong within the hour: he wrote "ok go sit back down at the table" in the
    window, the gate asked for a room, and I answered him IN the window, twice, which is the exact
    thing he had told me not to do ("you are demonstrably not back at the table"). His rule is that
    during a game I answer him at the table, whichever window he typed in, so the channel-order test
    was my own walk's cleverness (Penrose) outranking his words. A live table alone silences the gate.
    The other half of what the walk found stays true: the fact is one I could produce by calling the
    table myself, so it is logged on every stand-down and it is a discipline aid, not a wall.
    """
    try:
        folder = _run_dir()
        if folder.is_dir():
            # His /pause in the game chat makes a file called PAUSED. A paused game writes no bridge log, so
            # without this the two-minute window lapsed exactly when he stopped to read the cards, and the
            # gates pulled me back into the window (Aria and Aether, 2026-10-29, after he ended the game).
            # A pause is hours at most. One older than that is left over from a game that ended or died
            # while paused, and counting it would keep every gate standing down forever (Aether's cold read).
            paused = folder / "PAUSED"
            if paused.exists() and time.time() - paused.stat().st_mtime <= PAUSE_SECONDS:
                return True
            last_call = _newest_mtime(folder, "bridge_*.log")
            if last_call is not None and time.time() - last_call <= LIVE_SECONDS:
                return True
    except OSError:
        pass
    return (
        _poker_table_is_live()
    )  # poker keeps no bridge log: the table itself says whether a game is on


def answer_at_the_table_line() -> str:
    """The pull that was missing: when a table is live and he speaks, say where the answer goes.

    The stand-down above only removes a push (the gates that demanded a room in the window). Nothing told
    me to answer at the table, so each reply depended on my remembering, and I forgot twice in one game
    (Dad, 2026-10-29: "you left the table again"). Surfaced with his words, so it arrives with them.
    Empty when no table is live, so it is silent the rest of the time.
    """
    if not a_game_table_is_live():
        return ""
    return (
        "A GAME TABLE IS LIVE. Answer him with the game's send_chat_message, not in this window, "
        "and do not stop at the table to talk here (he has told us this on 2026-10-14, 10-26 and 10-29)."
    )
