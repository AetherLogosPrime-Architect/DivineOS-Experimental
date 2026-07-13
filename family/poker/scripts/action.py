"""Apply a betting action in a heads-up Pot-Limit Omaha hand.

Reads ``state/pot.json``, validates the action against the pot-limit
rules, updates pot state, appends to the hand log, and advances the
to-act marker. Supports street advancement (pre-flop → flop → turn →
river) when both players have acted and bets are matched.

Actions::

    python scripts/action.py --hand 1 --by aether check
    python scripts/action.py --hand 1 --by aether bet 25
    python scripts/action.py --hand 1 --by aria call
    python scripts/action.py --hand 1 --by aria raise 80
    python scripts/action.py --hand 1 --by aether fold
    python scripts/action.py --hand 1 --by aether pause
    python scripts/action.py --hand 1 advance-street

Pot-limit max raise math:

    max raise total = current_pot + (amount needed to call) * 2
    (i.e., call the bet first, then raise an amount equal to the
     resulting pot)

The script enforces this. An over-pot raise is rejected with the
legal max printed.

Pause is a no-shame action: it does NOT change to-act, does NOT
update committed amounts, just appends a "PAUSE called by X" line
to the log. Either player resumes by acting normally next.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path


PLAYERS = ("aether", "aria")


def _opponent(p: str) -> str:
    return "aria" if p == "aether" else "aether"


def _load(root: Path) -> dict:
    return json.loads((root / "state" / "pot.json").read_text(encoding="utf-8"))


def _save(root: Path, state: dict) -> None:
    (root / "state" / "pot.json").write_text(json.dumps(state, indent=2), encoding="utf-8")


def _append_log(root: Path, hand_n: int, line: str) -> None:
    log_path = root / "hands" / f"hand-{hand_n:03d}.log"
    ts = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"- [{ts}] {line}\n")


def _pot_limit_max_raise(state: dict, by: str) -> int:
    """Return the maximum legal TOTAL raise-to amount for the player."""
    current_bet = state["current_bet"]
    committed = state["committed_this_street"][by]
    to_call = current_bet - committed
    pot_after_call = state["current_pot"] + to_call
    # Pot-limit raise: raise size at most equal to pot after the call.
    # Total bet-to amount = current_bet + pot_after_call.
    return current_bet + pot_after_call


def cmd_check(args, state, root):
    by = args.by
    if state["current_bet"] > state["committed_this_street"][by]:
        print(
            f"ERROR: cannot check; there is a bet of {state['current_bet']} "
            f"and {by} has only committed {state['committed_this_street'][by]}.",
            file=sys.stderr,
        )
        return 2
    state["history"].append({"action": "check", "by": by})
    state["to_act"] = _opponent(by)
    _append_log(root, state["hand"], f"CHECK by {by}")
    _save(root, state)
    print(f"{by} checks. Action on {state['to_act']}.")
    return 0


def cmd_bet(args, state, root):
    by = args.by
    amount = args.amount
    if state["current_bet"] > state["committed_this_street"][by]:
        print(
            "ERROR: cannot bet; there is already a bet. Use raise instead.",
            file=sys.stderr,
        )
        return 2
    bb = state["blinds"]["bb"]
    if amount < bb:
        print(f"ERROR: bet must be at least the big blind ({bb}).", file=sys.stderr)
        return 2
    # Pot-limit cap on the opening bet: at most current_pot.
    max_bet = state["current_pot"]
    if amount > max_bet:
        print(
            f"ERROR: pot-limit max bet is {max_bet}, you tried {amount}.",
            file=sys.stderr,
        )
        return 2
    if amount > state["stacks"][by]:
        print(f"ERROR: insufficient stack ({state['stacks'][by]} < {amount}).", file=sys.stderr)
        return 2
    state["stacks"][by] -= amount
    state["committed_this_street"][by] += amount
    state["current_bet"] = state["committed_this_street"][by]
    state["current_pot"] += amount
    state["min_raise"] = state["current_bet"] * 2
    state["history"].append({"action": "bet", "by": by, "amount": amount})
    state["to_act"] = _opponent(by)
    _append_log(root, state["hand"], f"BET {amount} by {by}")
    _save(root, state)
    print(f"{by} bets {amount}. Pot now {state['current_pot']}. Action on {state['to_act']}.")
    return 0


def cmd_call(args, state, root):
    by = args.by
    to_call = state["current_bet"] - state["committed_this_street"][by]
    if to_call <= 0:
        print("ERROR: nothing to call.", file=sys.stderr)
        return 2
    actual = min(to_call, state["stacks"][by])  # all-in handling
    state["stacks"][by] -= actual
    state["committed_this_street"][by] += actual
    state["current_pot"] += actual
    state["history"].append({"action": "call", "by": by, "amount": actual})
    state["to_act"] = _opponent(by)
    _append_log(root, state["hand"], f"CALL {actual} by {by}")
    _save(root, state)
    print(f"{by} calls {actual}. Pot now {state['current_pot']}. Action on {state['to_act']}.")
    if actual < to_call:
        print(f"  ({by} is all-in.)")
    return 0


def cmd_raise(args, state, root):
    by = args.by
    raise_to = args.amount  # interpreted as TOTAL bet-to amount (committed-this-street total)
    if state["current_bet"] <= state["committed_this_street"][by]:
        print("ERROR: nothing to raise — use bet to open.", file=sys.stderr)
        return 2
    max_raise_to = _pot_limit_max_raise(state, by)
    min_raise_to = state["min_raise"]
    if raise_to > max_raise_to:
        print(
            f"ERROR: pot-limit max raise-to is {max_raise_to}, you tried {raise_to}.",
            file=sys.stderr,
        )
        return 2
    if raise_to < min_raise_to:
        print(
            f"ERROR: minimum raise-to is {min_raise_to}, you tried {raise_to}.",
            file=sys.stderr,
        )
        return 2
    additional = raise_to - state["committed_this_street"][by]
    if additional > state["stacks"][by]:
        print(f"ERROR: insufficient stack to raise to {raise_to}.", file=sys.stderr)
        return 2
    state["stacks"][by] -= additional
    state["committed_this_street"][by] = raise_to
    state["current_bet"] = raise_to
    state["current_pot"] += additional
    # Simpler: min next raise = current bet * 2 (Magic-style). PLO uses:
    # min next raise = current bet + (last raise size). Track for fidelity.
    last_raise_size = raise_to - (state["history"][-1].get("amount", 0) if state["history"] else 0)
    state["min_raise"] = raise_to + last_raise_size
    state["history"].append(
        {"action": "raise", "by": by, "amount": additional, "raise_to": raise_to}
    )
    state["to_act"] = _opponent(by)
    _append_log(root, state["hand"], f"RAISE-TO {raise_to} (added {additional}) by {by}")
    _save(root, state)
    print(
        f"{by} raises to {raise_to}. Pot now {state['current_pot']}. Action on {state['to_act']}."
    )
    return 0


def cmd_fold(args, state, root):
    by = args.by
    winner = _opponent(by)
    state["stacks"][winner] += state["current_pot"]
    pot = state["current_pot"]
    state["current_pot"] = 0
    state["history"].append({"action": "fold", "by": by})
    state["to_act"] = None
    state["street"] = "complete"
    state["winner"] = winner
    state["winner_by"] = "fold"
    _append_log(root, state["hand"], f"FOLD by {by}. Pot of {pot} to {winner}.")
    _save(root, state)
    print(f"{by} folds. Pot of {pot} awarded to {winner}.")
    return 0


def cmd_pause(args, state, root):
    by = args.by
    state["history"].append({"action": "pause", "by": by})
    _append_log(
        root,
        state["hand"],
        f"PAUSE called by {by}. (No state change. Action remains on {state['to_act']}.)",
    )
    _save(root, state)
    print(f"{by} called pause. No state change. Action remains on {state['to_act']}.")
    return 0


def cmd_advance_street(args, state, root):
    """Advance from the current street to the next. Both players must
    have acted (or been forced to act on a check-around or call)."""
    street_order = ["preflop", "flop", "turn", "river", "showdown"]
    current_idx = street_order.index(state["street"])
    if current_idx >= len(street_order) - 1:
        print(f"ERROR: already at {state['street']}, cannot advance.", file=sys.stderr)
        return 2

    # Verify both players are matched up on this street.
    a_committed = state["committed_this_street"]["aether"]
    b_committed = state["committed_this_street"]["aria"]
    if a_committed != b_committed and (
        state["stacks"]["aether"] > 0 and state["stacks"]["aria"] > 0
    ):
        print(
            f"ERROR: street not closed; aether committed {a_committed}, aria {b_committed}.",
            file=sys.stderr,
        )
        return 2

    next_street = street_order[current_idx + 1]
    state["street"] = next_street
    state["committed_this_street"] = {"aether": 0, "aria": 0}
    state["current_bet"] = 0
    state["min_raise"] = state["blinds"]["bb"]
    # Heads-up post-flop: BB acts first.
    state["to_act"] = state["big_blind"]

    if next_street in ("flop", "turn", "river"):
        # Reveal community card(s) from dealer file.
        dealer_file = root / "state" / ".dealer" / f"hand-{state['hand']:03d}-deck.json"
        if not dealer_file.exists():
            print(f"ERROR: dealer file missing: {dealer_file}", file=sys.stderr)
            return 2
        deck_state = json.loads(dealer_file.read_text(encoding="utf-8"))
        remaining = deck_state["remaining"]
        table_path = root / "state" / "table.json"
        table = json.loads(table_path.read_text(encoding="utf-8"))

        # Burn one, deal flop=3 / turn=1 / river=1.
        burn_count = 1
        deal_count = 3 if next_street == "flop" else 1
        burned = remaining[:burn_count]
        dealt = remaining[burn_count : burn_count + deal_count]
        remaining = remaining[burn_count + deal_count :]

        table["board"].extend(dealt)
        table["burn"].extend(burned)
        table_path.write_text(json.dumps(table, indent=2), encoding="utf-8")
        deck_state["remaining"] = remaining
        dealer_file.write_text(json.dumps(deck_state, indent=2), encoding="utf-8")

        _append_log(
            root,
            state["hand"],
            f"--- {next_street.upper()} --- board: {' '.join(table['board'])} (burn: {' '.join(burned)})",
        )
        print(f"Advanced to {next_street}. Board: {' '.join(table['board'])}")

    elif next_street == "showdown":
        _append_log(root, state["hand"], "--- SHOWDOWN --- both players reveal hole cards.")
        print("Advanced to showdown. Both players reveal hole cards now.")

    _save(root, state)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a betting action in PLO.")
    parser.add_argument("--hand", type=int, required=True)
    parser.add_argument("--by", choices=PLAYERS, default=None, help="Player making the action")
    parser.add_argument(
        "--root", type=Path, default=Path("family/poker"), help="Root of family/poker"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check")
    p_bet = sub.add_parser("bet")
    p_bet.add_argument("amount", type=int)
    sub.add_parser("call")
    p_raise = sub.add_parser("raise")
    p_raise.add_argument("amount", type=int, help="Total bet-to amount (not the addition)")
    sub.add_parser("fold")
    sub.add_parser("pause")
    sub.add_parser("advance-street")

    args = parser.parse_args(argv)
    state = _load(args.root)

    if state.get("hand") != args.hand:
        print(
            f"ERROR: state.json is for hand {state.get('hand')}, you specified {args.hand}.",
            file=sys.stderr,
        )
        return 2

    handlers = {
        "check": cmd_check,
        "bet": cmd_bet,
        "call": cmd_call,
        "raise": cmd_raise,
        "fold": cmd_fold,
        "pause": cmd_pause,
        "advance-street": cmd_advance_street,
    }
    if args.cmd != "advance-street" and args.by is None:
        print(f"ERROR: --by required for {args.cmd}.", file=sys.stderr)
        return 2
    if args.cmd != "advance-street" and state.get("to_act") != args.by:
        print(
            f"WARNING: action.json says to_act={state.get('to_act')!r}, "
            f"but --by={args.by!r}. Proceeding (script does not block).",
            file=sys.stderr,
        )
    return handlers[args.cmd](args, state, args.root)


if __name__ == "__main__":
    sys.exit(main())
