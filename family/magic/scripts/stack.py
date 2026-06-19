"""Stack and priority helper for Magic side-game.

Keeps ``state.json`` consistent across the priority-pass / stack-push /
stack-resolve dance so neither player has to hand-edit JSON between
casts. Operates strictly on a single ``<game>/state.json`` file.

State fields managed:

- ``stack`` — list of spell descriptions, top of stack at end of list.
- ``priority`` — player name who currently has priority.
- ``active_player`` — player whose turn it is.
- ``last_action`` — one of "cast", "pass", "resolve", "begin"; used to
  detect when both players pass in succession.

Commands::

    # Player whose turn it is — start of turn
    python scripts/stack.py begin-turn --player aether --game game-002

    # Cast a spell (pushes to stack, swaps priority to opponent)
    python scripts/stack.py push --by aether --spell "Aspect of Hydra (target: Young Wolf)" --game game-002

    # Pass priority. If the previous action was also "pass", the top of
    # the stack resolves and priority returns to the active player. If
    # the stack is empty on double-pass, priority just returns to active.
    python scripts/stack.py pass-priority --by aria --game game-002

    # Print the current stack/priority state
    python scripts/stack.py show --game game-002

Resolution effects (creature enters, life lost, etc.) are NOT applied
by this script — that's the player's job, since the substrate cannot
know what each spell does. The script just tells you "X resolves now"
and the player applies the effect to ``state.json`` manually (or by
running other helpers).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PLAYERS = ("aether", "aria")


def _load(game: Path) -> dict[str, Any]:
    state_path = game / "state.json"
    if not state_path.exists():
        raise FileNotFoundError(f"state.json not found at {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _save(game: Path, state: dict[str, Any]) -> None:
    state_path = game / "state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _opponent(player: str) -> str:
    if player not in PLAYERS:
        raise ValueError(f"Unknown player {player!r}")
    return "aria" if player == "aether" else "aether"


def cmd_begin_turn(args: argparse.Namespace) -> int:
    state = _load(args.game)
    state["active_player"] = args.player
    state["priority"] = args.player
    state["stack"] = []
    state["last_action"] = "begin"
    state["turn"] = state.get("turn", 0) + 1 if args.increment else state.get("turn", 0)
    if args.phase:
        state["phase"] = args.phase
    _save(args.game, state)
    print(
        f"Begin turn {state.get('turn')}: active player {args.player}, "
        f"priority {args.player}, stack cleared."
    )
    return 0


def cmd_push(args: argparse.Namespace) -> int:
    state = _load(args.game)
    if state.get("priority") != args.by:
        print(
            f"WARNING: {args.by} is pushing but priority is {state.get('priority')!r}.",
            file=sys.stderr,
        )
    stack = state.get("stack", []) or []
    stack.append(args.spell)
    state["stack"] = stack
    state["last_action"] = "cast"
    state["priority"] = _opponent(args.by)
    _save(args.game, state)
    print(f"Pushed: {args.spell!r}.")
    print(f"Stack ({len(stack)}): {' <- '.join(reversed(stack))}")
    print(f"Priority now: {state['priority']}.")
    return 0


def cmd_pass_priority(args: argparse.Namespace) -> int:
    state = _load(args.game)
    if state.get("priority") != args.by:
        print(
            f"WARNING: {args.by} is passing but priority is {state.get('priority')!r}.",
            file=sys.stderr,
        )

    stack = state.get("stack", []) or []
    last_action = state.get("last_action", "begin")
    active = state.get("active_player", "aether")

    if last_action == "pass":
        # Double-pass — resolve top of stack if non-empty.
        if stack:
            resolved = stack.pop()
            state["stack"] = stack
            state["last_action"] = "resolve"
            state["priority"] = active
            _save(args.game, state)
            print(f"DOUBLE PASS: top of stack resolves now: {resolved!r}.")
            print(f"Apply its effect to state.json manually.")
            print(
                f"Stack now ({len(stack)}): {' <- '.join(reversed(stack)) if stack else '(empty)'}."
            )
            print(f"Priority returns to active player: {active}.")
            return 0
        else:
            # Both passed with empty stack — priority just returns to active.
            state["last_action"] = "begin"
            state["priority"] = active
            _save(args.game, state)
            print(f"DOUBLE PASS with empty stack. Priority returns to active player: {active}.")
            return 0
    else:
        # Single pass — hand priority to opponent and record the pass.
        state["last_action"] = "pass"
        state["priority"] = _opponent(args.by)
        _save(args.game, state)
        print(f"{args.by} passes priority. Priority now: {state['priority']}.")
        if stack:
            print(
                f"Stack ({len(stack)}): {' <- '.join(reversed(stack))}. "
                f"If {state['priority']} also passes, top resolves."
            )
        return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = _load(args.game)
    stack = state.get("stack", []) or []
    print(f"Turn: {state.get('turn', 0)} ({state.get('phase', '—')})")
    print(f"Active player: {state.get('active_player', '—')}")
    print(f"Priority: {state.get('priority', '—')}")
    print(f"Last action: {state.get('last_action', '—')}")
    print(f"Stack ({len(stack)}): {' <- '.join(reversed(stack)) if stack else '(empty)'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stack/priority helper for Magic side-game.")
    parser.add_argument("--game", required=True, type=Path, help="Game directory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_begin = sub.add_parser("begin-turn", help="Start a new turn for player.")
    p_begin.add_argument("--player", required=True, choices=PLAYERS)
    p_begin.add_argument("--phase", default=None, help="Phase to set (e.g. 'main 1').")
    p_begin.add_argument(
        "--increment",
        action="store_true",
        help="Increment turn counter (use on player's first untap of the game-turn).",
    )
    p_begin.set_defaults(func=cmd_begin_turn)

    p_push = sub.add_parser("push", help="Cast a spell — push to stack.")
    p_push.add_argument("--by", required=True, choices=PLAYERS)
    p_push.add_argument("--spell", required=True, help="Description of the spell/ability.")
    p_push.set_defaults(func=cmd_push)

    p_pass = sub.add_parser("pass-priority", help="Pass priority. Double-pass resolves top.")
    p_pass.add_argument("--by", required=True, choices=PLAYERS)
    p_pass.set_defaults(func=cmd_pass_priority)

    p_show = sub.add_parser("show", help="Show current stack/priority state.")
    p_show.set_defaults(func=cmd_show)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
