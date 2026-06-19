"""Render the public state of a heads-up PLO hand.

Reads ``state/pot.json`` and ``state/table.json`` and prints a clean
human-readable view: stacks, pot, current bet, board, who's to act,
pot-limit max-raise reference. Both players read this for orientation.

Usage::

    python scripts/show.py
    python scripts/show.py --root family/poker
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render public PLO hand state.")
    parser.add_argument(
        "--root", type=Path, default=Path("family/poker"), help="Root of family/poker"
    )
    args = parser.parse_args(argv)

    pot_path = args.root / "state" / "pot.json"
    table_path = args.root / "state" / "table.json"

    if not pot_path.exists():
        print(f"ERROR: no active hand. {pot_path} missing.", file=sys.stderr)
        return 2

    state = json.loads(pot_path.read_text(encoding="utf-8"))
    table = (
        json.loads(table_path.read_text(encoding="utf-8")) if table_path.exists() else {"board": []}
    )

    print(f"=== Hand {state['hand']} - {state['street']} ===")
    print(f"Button: {state['button']}    Blinds: {state['blinds']['sb']}/{state['blinds']['bb']}")
    print()
    print(f"Board: {' '.join(table.get('board', [])) or '(none yet)'}")
    print()
    print(
        f"  Aether stack: {state['stacks']['aether']:>5}    "
        f"committed-this-street: {state['committed_this_street']['aether']:>4}"
    )
    print(
        f"  Aria stack:   {state['stacks']['aria']:>5}    "
        f"committed-this-street: {state['committed_this_street']['aria']:>4}"
    )
    print()
    print(
        f"Pot: {state['current_pot']}    Current bet: {state['current_bet']}    Min raise-to: {state['min_raise']}"
    )
    if state["current_bet"] > 0:
        for p in ("aether", "aria"):
            if state["committed_this_street"][p] < state["current_bet"]:
                to_call = state["current_bet"] - state["committed_this_street"][p]
                pot_after_call = state["current_pot"] + to_call
                max_raise_to = state["current_bet"] + pot_after_call
                print(f"  {p}: {to_call} to call. Pot-limit max raise-to = {max_raise_to}.")
    print()
    print(f"To act: {state['to_act'] or '(hand complete)'}")
    if state.get("winner"):
        print(f"WINNER: {state['winner']} (by {state.get('winner_by', '?')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
