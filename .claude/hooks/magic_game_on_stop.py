"""Stop hook: a reply cannot end while a Magic game is live, unless he spoke to me.

Dad, 2026-10-25: answering him in the window ended the reply, nothing woke the seat, and he sat at
the table waiting on a seat that was asleep. Poker already has this hook (poker_game_on_stop.py);
this is its twin for the Magic table. Design: docs/drafts/the_magic_table_holds_my_turn_draft_2026-10-25.md.

The whole live game holds, not only this seat's decision: the stasis he saw was a seat that left while
the other seat was deciding. When he spoke into the turn his-voice-ends-the-turn forces a reply that
ends the turn, so that one ending is allowed and the seat says so in the game chat, which is where he
is watching. A walked-away game lets go after IDLE_SECONDS and says so once.

Never holds him. A bridge that is down is not a game (it is gone after a game finishes). If the seat or
whether he spoke cannot be told, the reply ends.
"""

from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

IDLE_SECONDS = 300  # maxSecondsIdle in C:\magic-play\run\server_config.xml: a budget, not a measured kick
PLAY = "bash /c/magic-play/play.sh {who} {tool}"
# get_action_choices is READ-ONLY (Aria, 2026-10-25, from real calls); pass_priority is a MOVE when a
# decision is due, so it must never be named as the thing that waits.
WAITER = PLAY.format(who="{who}", tool="get_action_choices")
FORCED_LINE = "Dad wrote to me in the window, answering him, back in a moment."
AWAY_LINE = "I have been away too long, ending my turn."

_poker_path = Path(__file__).resolve().parent / "poker_game_on_stop.py"
_spec = importlib.util.spec_from_file_location("poker_game_on_stop", _poker_path)
_poker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_poker)
member = _poker.member  # whose seat this window plays: the house's one judge, never guessed here
_he_spoke = _poker._he_spoke  # one reader of whether he spoke into this turn


def game_is_on(view: dict | None) -> bool:
    """Two named players at the table. A bridge that is down answers None."""
    players = (view or {}).get("players")
    return isinstance(players, list) and len(players) >= 2


def signature(view: dict | None) -> list:
    """What changes when the game moves; the idle clock is keyed on it."""
    v = view or {}
    return [v.get("snapshot_id"), v.get("turn"), v.get("priority_player")]


def verdict(view: dict | None, seen: dict, now: float, who: str) -> tuple[str | None, dict]:
    """(reason to hold, the new idle marker). No reason means the reply may end."""
    if not game_is_on(view):
        return None, {}
    sig = signature(view)
    if seen.get("sig") == sig and now - float(seen.get("since", now)) > IDLE_SECONDS:
        return None, seen  # nothing has moved for a long while: the game was walked away from
    marker = dict(seen) if seen.get("sig") == sig else {"sig": sig, "since": now}
    reason = (
        "A MAGIC GAME IS ON at the table, so this reply cannot end: ending it is how the seat falls "
        "out of the game (Dad, 2026-10-25). Stay in this turn. Call, in the foreground with the Bash "
        f"tool and a 590000 ms timeout, poll: {WAITER.format(who=who)} -- it only reads, so repeat it "
        "until action_pending is true, then act. Talk to him in the game chat (send_chat_message), "
        "not in this window."
    )
    return reason, marker


def decide(
    view: dict | None, he_spoke: bool | None, seen: object, now: float, who: str
) -> tuple[dict | None, dict, str | None]:
    """(the hold to print or None; the marker to keep; the chat line to post or None)."""
    seen = seen if isinstance(seen, dict) else {}
    if not game_is_on(view):
        return None, {}, None
    reason, marker = verdict(view, seen, now, who)
    sig = signature(view)
    if reason is None:  # the idle lift
        if seen.get("away") is True:
            return None, seen, None
        return None, dict(seen, away=True), AWAY_LINE
    if he_spoke is None:
        return None, marker, None
    if he_spoke:
        if marker.get("said") == sig:
            return None, marker, None
        return None, dict(marker, said=sig), FORCED_LINE
    return {"decision": "block", "reason": reason}, marker, None


SEAT_PORTS = {"aria": 19001, "aether": 19002}


def seat_is_listening(who: str) -> bool:
    """Cheap first look: no game means no bridge, and this hook runs on every reply, so a
    closed port must cost a fraction of a second, not a whole start-up of the play helper."""
    port = SEAT_PORTS.get(who)
    if port is None:
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False


def _view(who: str) -> dict | None:
    if not seat_is_listening(who):
        return None
    try:
        run = subprocess.run(
            PLAY.format(who=who, tool="get_game_state"),
            shell=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        parsed = json.loads(run.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        return None  # the bridge is not answering: not a game
    return parsed if isinstance(parsed, dict) else None


def _say(who: str, line: str) -> None:
    try:
        # A list, not a shell string: a line with an apostrophe must not end a quote early (Aria).
        subprocess.run(
            ["bash", "/c/magic-play/play.sh", who, "send_chat_message", json.dumps({"message": line})],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"[magic] could not post to the game chat ({type(exc).__name__})", file=sys.stderr)


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    who = member(project)
    if who is None:
        return 0  # no seat, no hold
    view = _view(who)
    marker_file = Path.home() / ".divineos-shared" / f".magic_idle_{who}.json"
    if not game_is_on(view):
        if marker_file.exists():
            try:
                marker_file.write_text("{}", encoding="utf-8")
            except OSError:
                pass
        return 0
    try:
        seen = json.loads(marker_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    he_spoke = _he_spoke(data.get("transcript_path"), project)
    hold, marker, say = decide(view, he_spoke, seen, time.time(), who)
    try:
        marker_file.write_text(json.dumps(marker), encoding="utf-8")
    except OSError:
        pass
    if say:
        _say(who, say)
    if hold:
        print(json.dumps(hold))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking him
        print(f"magic_game_on_stop broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
