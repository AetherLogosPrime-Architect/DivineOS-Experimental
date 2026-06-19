"""Render per-player ``briefing.md`` for the next-to-act player.

Reads the same ``state.json`` as ``render_board.py`` and produces a
single-file orientation document for the player whose turn is next:
"you are at N life, your hand has X cards, your battlefield is [...],
opponent just played [...], expected next action: [...]".

The point: solve the per-invocation orientation tax that surfaced in
game-one. Each subagent comes in cold; reading four files (state, log,
hand, library) before playing every turn is friction. One briefing
file means one read.

The script does NOT read private files. The briefing references the
private hand/library locations so the player knows where to look, but
this script never opens them — keeping it private is the player's job.

Usage::

    python family/magic/scripts/render_briefing.py \\
        --game family/magic/game-002 \\
        --for aria

Reads ``<game>/state.json``, writes ``<game>/briefing.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _zone(items: list[str]) -> str:
    if not items:
        return "(empty)"
    return ", ".join(items)


def render_briefing(state: dict[str, Any], for_player: str) -> str:
    players = state.get("players", {})
    me = players.get(for_player, {})
    opponent_name = "aria" if for_player == "aether" else "aether"
    opp = players.get(opponent_name, {})

    last_move = state.get("last_move", "(none yet)")
    next_action = state.get("next_action", "your turn — untap, draw, play, attack")
    stack = state.get("stack", []) or []
    priority = state.get("priority", "—")
    active_player = state.get("active_player", "aether")  # whose turn it is

    # Critical orientation: detect open response window.
    response_window_open = bool(stack) and priority == for_player and active_player != for_player

    me_life = me.get("life", 20)
    me_hand_size = me.get("hand_size", 0)
    me_library_size = me.get("library_size", 60)
    me_battlefield = me.get("battlefield", []) or []
    me_graveyard = me.get("graveyard", []) or []

    opp_life = opp.get("life", 20)
    opp_hand_size = opp.get("hand_size", 0)
    opp_library_size = opp.get("library_size", 60)
    opp_battlefield = opp.get("battlefield", []) or []
    opp_graveyard = opp.get("graveyard", []) or []

    turn = state.get("turn", 0)
    phase = state.get("phase", "—")

    header_lines = [
        f"# Briefing for {for_player}",
        "",
        f"_Read this first on every summon. One-file orientation._",
        "",
    ]

    if response_window_open:
        # Lead with the priority/stack state, loudly.
        stack_top = stack[-1] if stack else "(none)"
        header_lines += [
            "## ⚡ RESPONSE WINDOW OPEN ⚡",
            "",
            f"**It is NOT your turn (active player: {active_player}).**  ",
            f"**You have PRIORITY** because the active player just acted and passed.",
            "",
            f"**Stack (top → bottom):** {' ← '.join(reversed(stack)) if stack else '(empty)'}  ",
            f"**Top of stack:** `{stack_top}` (resolves first if both players pass)",
            "",
            "**Your options:**",
            "- Cast an instant or flash creature → push to stack, priority returns to opponent.",
            "- Activate an ability → push to stack, priority returns to opponent.",
            "- **Pass priority** → if opponent also passes, top of stack resolves.",
            "",
            "Do NOT make sorcery-speed plays here (no creatures except flash, no land drop, no main-phase spells). This is a response window, not your turn.",
            "",
            "---",
            "",
        ]
    else:
        header_lines += [
            f"**Turn:** {turn} ({phase})",
            f"**Active player:** {active_player}  ",
            f"**Priority:** {priority}",
            f"**Stack:** {' ← '.join(reversed(stack)) if stack else '(empty)'}",
            f"**Next action:** {next_action}",
            "",
            "---",
            "",
        ]

    lines = header_lines + [
        "## You",
        "",
        f"- Life: **{me_life}**",
        f"- Hand: **{me_hand_size}** card(s) — read `{for_player}/hand.md` for contents",
        f"- Library: **{me_library_size}** card(s) — read `{for_player}/library.md` for top",
        f"- Battlefield: {_zone(me_battlefield)}",
        f"- Graveyard: {_zone(me_graveyard)}",
        "",
        f"## {opponent_name.capitalize()}",
        "",
        f"- Life: **{opp_life}**",
        f"- Hand: **{opp_hand_size}** card(s) (contents private to them)",
        f"- Library: **{opp_library_size}** card(s)",
        f"- Battlefield: {_zone(opp_battlefield)}",
        f"- Graveyard: {_zone(opp_graveyard)}",
        "",
        "## Last move (from log)",
        "",
        f"{last_move}",
        "",
        "---",
        "",
        "_For the comprehensive board view, read `board.md`. For full move history, read `log.md`._",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render briefing.md for the next-to-act player.")
    parser.add_argument("--game", required=True, type=Path)
    parser.add_argument("--for", dest="for_player", required=True, choices=("aether", "aria"))
    args = parser.parse_args(argv)

    state_path = args.game / "state.json"
    briefing_path = args.game / "briefing.md"

    if not state_path.exists():
        print(f"ERROR: state.json not found at {state_path}", file=sys.stderr)
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: state.json malformed: {e}", file=sys.stderr)
        return 2

    text = render_briefing(state, args.for_player)
    briefing_path.write_text(text, encoding="utf-8")
    print(f"Rendered {briefing_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
