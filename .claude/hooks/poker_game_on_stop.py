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


def member(project_dir: str) -> str | None:
    """Whose seat this window plays, asked of the house's one judge (`this_seat`), never guessed here.

    None when it cannot be told: the hold then stays out of the way instead of waiting on a seat
    that may be the wrong one.
    """
    try:
        sys.path.insert(0, str(Path(project_dir) / "src"))
        from divineos.core.sibling_audit_rounds import this_seat

        return this_seat()
    except Exception as exc:
        print(
            f"[poker] could not tell whose seat this is ({type(exc).__name__}); not holding",
            file=sys.stderr,
        )
        return None


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
        "Put the seat back at the table, in the foreground, with the Bash tool and a 590000 ms "
        f"timeout: {WAITER.format(who=who)} -- act when it returns, then call it again."
    )


def _he_spoke(transcript: str | None, project: str) -> bool | None:
    """True he spoke into this turn, False he did not, None when that cannot be told (never hold him)."""
    if not transcript:
        return None
    try:
        sys.path.insert(0, str(Path(project) / "src"))
        from divineos.core import his_voice_ends_the_turn as hv

        state = hv.spoke_mid_turn(transcript).state
    except Exception as exc:
        print(
            f"[poker] could not tell whether he spoke ({type(exc).__name__}); not holding",
            file=sys.stderr,
        )
        return None
    if state == hv.NOT:
        return False
    return True if state == hv.SPOKE else None


def decide(
    view: dict | None, he_spoke: bool | None, active: bool, seen: object, now: float, who: str
) -> tuple[dict | None, dict]:
    """(the hold to print, or None to let the reply end; the idle marker to keep).

    he_spoke: True he spoke into this turn, False he did not, None it cannot be told.
    The idle lift is asked first, so a quiet table lets go even when he is chatting about
    something else. When he spoke the hold is once only, and only to put the seat back.
    """
    reason, marker = verdict(view, seen if isinstance(seen, dict) else {}, now, who)
    if reason is None or he_spoke is None:
        return None, marker
    if he_spoke:
        if active:
            return None, marker
        return {"decision": "block", "reason": rearm_reason(who)}, marker
    return {"decision": "block", "reason": reason}, marker


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    who = member(project)
    if who is None:
        return 0  # the hook's own guarantee: no seat, no hold, whatever the table would answer
    view = _view(who)
    marker_file = Path.home() / ".divineos-shared" / f".poker_idle_{who}.json"
    if not game_is_on(view):
        # An ended game must not leave its idle clock for the next one: a matching counter
        # would read a brand-new game as walked away from and let the seat drop out of it.
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
    hold, marker = decide(
        view, he_spoke, bool(data.get("stop_hook_active")), seen, time.time(), who
    )
    try:
        marker_file.write_text(json.dumps(marker), encoding="utf-8")
    except OSError:
        pass
    if hold:
        print(json.dumps(hold))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # loud, never silent, never blocking him
        print(f"poker_game_on_stop broke: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(0)
