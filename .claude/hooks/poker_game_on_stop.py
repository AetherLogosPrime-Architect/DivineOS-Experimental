"""Stop hook: a reply cannot end while a poker game is on at the table, unless he spoke to me.

Dad, 2026-10-15: the family poker table kept dropping Aether, because Aether ended its own turn
between hands, after which nothing woke it ("make it structural so you dont need to remember").
What woke a seat was a call the seat had to remember to make again, and memory failed. This reads
the table itself: while a hand is live, or the table is about to deal the next one, a reply that
tries to end is held with the one command that keeps the seat in the game.

Never holds him. If he spoke into this turn (his-voice-ends-the-turn's own check), or that check
cannot be run, the reply ends. A table that is down is not a game. A table whose move counter has
not moved for IDLE_SECONDS is not a game either, so a walked-away game cannot trap a seat forever.
Holds on every attempt, not once: the one-hold-per-reply shape would let the second try through.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

IDLE_SECONDS = 600
TABLE = "http://127.0.0.1:8765"
WAITER = "python /c/poker-play/wait_turn.py {who} 580"


def member(project_dir: str) -> str:
    return "aria" if "aria" in project_dir.lower() else "aether"


def game_is_on(view: dict | None) -> bool:
    """A hand is live, or the table is counting down to deal the next one."""
    if not view or view.get("hand") is None:
        return False
    return bool(view.get("live")) or view.get("deal_in") is not None


def verdict(view: dict | None, seen: dict, now: float, who: str) -> tuple[str | None, dict]:
    """(reason to hold, the new idle marker). No reason means the reply may end."""
    if not game_is_on(view):
        return None, {}
    turn = (view or {}).get("turn")
    if seen.get("turn") == turn and now - float(seen.get("since", now)) > IDLE_SECONDS:
        return None, seen  # nothing has moved for a long while: the game was walked away from
    marker = seen if seen.get("turn") == turn else {"turn": turn, "since": now}
    reason = (
        "A POKER GAME IS ON at the table, so this reply cannot end: ending it is how the seat "
        "falls out of the game (Dad, 2026-10-15). Stay in this turn. Call, in the foreground with "
        f"the Bash tool and a 590000 ms timeout: {WAITER.format(who=who)} -- act when it returns, "
        "then call it again, and keep going. If he typed to you in this window, answer him instead; "
        "that is never held."
    )
    return reason, marker


def _view(who: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{TABLE}/state?seat={who}", timeout=1.5) as r:
            return json.load(r)
    except (OSError, ValueError):
        return None  # the table is not answering: not a game


def rearm_reason(who: str) -> str:
    """When he spoke: his reply was already read, so this only puts the seat back at the table."""
    return (
        "A POKER GAME IS ON and he spoke to you, so your reply to him stands. Do not re-post it. "
        "Put the seat back at the table so the game can wake you: Bash with run_in_background: "
        f"true, command: {WAITER.format(who=who)} -- it ends on your turn, which is what wakes you."
    )


def _he_spoke_or_unknown(transcript: str | None, project: str) -> bool:
    """True when he spoke into this turn, or when that cannot be told: never hold him."""
    if not transcript:
        return True
    try:
        sys.path.insert(0, str(Path(project) / "src"))
        from divineos.core import his_voice_ends_the_turn as hv

        return hv.spoke_mid_turn(transcript).state != hv.NOT
    except Exception as exc:
        print(f"[poker] could not tell whether he spoke ({type(exc).__name__}); not holding", file=sys.stderr)
        return True


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    who = member(project)
    view = _view(who)
    if not game_is_on(view):
        return 0
    if _he_spoke_or_unknown(data.get("transcript_path"), project):
        if not data.get("stop_hook_active") and data.get("transcript_path"):
            print(json.dumps({"decision": "block", "reason": rearm_reason(who)}))
        return 0
    marker_file = Path.home() / ".divineos-shared" / f".poker_idle_{who}.json"
    try:
        seen = json.loads(marker_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    reason, marker = verdict(view, seen, time.time(), who)
    try:
        marker_file.write_text(json.dumps(marker), encoding="utf-8")
    except OSError:
        pass
    if reason:
        print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking him
        print(f"poker_game_on_stop broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
