"""Render comprehensive ``board.md`` for a Magic side-game.

Reads a small JSON state file (``state.json`` in the game directory)
and produces ``board.md`` — the kitchen-table view of everything the
two players are *allowed* to see. Both battlefields, both graveyards,
both life totals, hand sizes (not contents), library sizes (not
contents), the stack, the current turn/phase/priority.

The JSON shape is intentionally small and human-editable. Players
update ``state.json`` directly during play; this script regenerates
``board.md`` so the human-readable view stays in sync.

Schema (all fields optional, defaults sane)::

    {
      "format": "Pauper",
      "rules": "standard",
      "turn": 3,
      "phase": "main 1",
      "priority": "aether",
      "stack": [],
      "players": {
        "aether": {
          "life": 20,
          "hand_size": 5,
          "library_size": 53,
          "battlefield": ["1 Forest (T)", "Elvish Mystic (T)"],
          "graveyard": [],
          "exile": [],
          "mana_pool": []
        },
        "aria": { ... }
      }
    }

Usage::

    python family/magic/scripts/render_board.py \\
        --game family/magic/game-002

Reads ``<game>/state.json``, writes ``<game>/board.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _zone(items: list[str], empty: str = "(empty)") -> str:
    if not items:
        return empty
    return ", ".join(items)


def _section(title: str, body: str) -> str:
    return f"### {title}\n\n{body}\n"


def _player_block(name: str, p: dict[str, Any]) -> str:
    life = p.get("life", 20)
    hand_size = p.get("hand_size", 0)
    library_size = p.get("library_size", 60)
    battlefield = p.get("battlefield", []) or []
    graveyard = p.get("graveyard", []) or []
    exile = p.get("exile", []) or []
    mana_pool = p.get("mana_pool", []) or []

    lines = [
        f"## {name.capitalize()}",
        "",
        f"- **Life:** {life}",
        f"- **Hand:** {hand_size} card(s) (contents private)",
        f"- **Library:** {library_size} card(s) (top private)",
        "",
        f"**Battlefield:** {_zone(battlefield)}",
        "",
        f"**Graveyard:** {_zone(graveyard)}",
        "",
        f"**Exile:** {_zone(exile)}",
        "",
        f"**Mana pool:** {_zone(mana_pool)}",
        "",
    ]
    return "\n".join(lines)


def render_board(state: dict[str, Any]) -> str:
    fmt = state.get("format", "Pauper")
    rules = state.get("rules", "standard")
    turn = state.get("turn", 0)
    phase = state.get("phase", "—")
    priority = state.get("priority", "—")
    stack = state.get("stack", []) or []
    players = state.get("players", {})

    header = [
        "# Board view",
        "",
        f"_Comprehensive visible game state. Both players read this. Generated from state.json._",
        "",
        f"- **Format:** {fmt}",
        f"- **Rules:** {rules}",
        f"- **Turn:** {turn}",
        f"- **Phase:** {phase}",
        f"- **Priority:** {priority}",
        f"- **Stack:** {_zone(stack, '(empty)')}",
        "",
        "---",
        "",
    ]

    body = []
    for player_name in ("aether", "aria"):
        p = players.get(player_name, {})
        body.append(_player_block(player_name, p))

    return "\n".join(header) + "\n".join(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render board.md from state.json for a magic game."
    )
    parser.add_argument(
        "--game",
        required=True,
        type=Path,
        help="Game directory (e.g. family/magic/game-002)",
    )
    args = parser.parse_args(argv)

    state_path = args.game / "state.json"
    board_path = args.game / "board.md"

    if not state_path.exists():
        print(f"ERROR: state.json not found at {state_path}", file=sys.stderr)
        return 2

    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: state.json malformed: {e}", file=sys.stderr)
        return 2

    text = render_board(state)
    board_path.write_text(text, encoding="utf-8")
    print(f"Rendered {board_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
