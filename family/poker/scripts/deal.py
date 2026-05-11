"""Deal a fresh hand of heads-up Pot-Limit Omaha.

Shuffles a 52-card deck, deals 4 hole cards to each player into their
private subdir (``aether/hole.md``, ``aria/hole.md``), and appends a
SHA256 commitment to the public per-hand log. Initializes
``state/pot.json`` and ``state/table.json`` for the new hand.

The hash commitment is the integrity feature Aria specified: each
player's 4 hole cards are hashed at deal time, and the hash is in the
public log. At showdown the revealed cards are re-hashed and verified
against the commit, so neither player can swap a card mid-hand.

The randomness is wall-clock seeded by default. ``--seed N`` makes
shuffles reproducible (useful for testing; never use in real play).

Usage::

    python scripts/deal.py --hand 1 --button aether

Required:
    --hand N       Hand number (e.g. 1, 2, 3...). Used in filenames.
    --button NAME  Which player has the button this hand (alternates).

Optional:
    --seed N       Reproducible shuffle. Omit for true randomness.
    --root PATH    Root of family/poker (default: family/poker).

Idempotency: refuses to overwrite an existing hand-NNN.log. Delete
the file by hand if you want to re-deal.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import random
import sys
import time
from pathlib import Path


# Standard 52-card deck. Suit order: c d h s. Rank order: 2 3 4 5 6 7 8 9 T J Q K A.
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
SUITS = ["c", "d", "h", "s"]
DECK = [r + s for r in RANKS for s in SUITS]
PLAYERS = ("aether", "aria")


def _hash_cards(cards: list[str]) -> str:
    """SHA256 a sorted-then-joined card list. Sorting makes the commit
    independent of deal-order, so revealing cards in any order verifies."""
    canonical = ",".join(sorted(cards))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_hole(player_dir: Path, hand_n: int, cards: list[str], commit: str) -> None:
    player_dir.mkdir(parents=True, exist_ok=True)
    hole_path = player_dir / "hole.md"
    body = [
        f"# Hole cards (private — opponent does NOT read)",
        "",
        f"Hand: {hand_n}",
        f"Commit: {commit}",
        "",
        f"## Cards",
        "",
    ]
    body.extend(f"- {c}" for c in cards)
    body.append("")
    body.append("(Reveal these AT SHOWDOWN, not before. Re-hash to confirm against commit.)")
    body.append("")
    hole_path.write_text("\n".join(body), encoding="utf-8")

    # Append to per-player commits log (auditable history).
    commits_log = player_dir / "commits.log"
    line = f"{datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()}Z hand={hand_n} commit={commit}\n"
    with commits_log.open("a", encoding="utf-8") as f:
        f.write(line)


def _write_state(state_dir: Path, hand_n: int, button: str, blinds: tuple[int, int]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    sb, bb = blinds
    other = "aria" if button == "aether" else "aether"

    # Heads-up rules: button posts SB and acts first pre-flop.
    pot = {
        "hand": hand_n,
        "street": "preflop",
        "button": button,
        "small_blind": button,
        "big_blind": other,
        "blinds": {"sb": sb, "bb": bb},
        "stacks": {"aether": 1000, "aria": 1000},  # 100bb each at 5/10
        "committed_this_street": {"aether": 0, "aria": 0},
        "current_pot": 0,
        "current_bet": bb,  # BB is live as opening bet
        "to_act": button,  # button acts first pre-flop in HU
        "min_raise": bb * 2,
        "history": [],
    }
    # Apply forced blinds to stacks and pot.
    pot["stacks"][button] -= sb
    pot["stacks"][other] -= bb
    pot["committed_this_street"][button] = sb
    pot["committed_this_street"][other] = bb
    pot["current_pot"] = sb + bb
    pot["history"].append(
        {"action": "post_sb", "by": button, "amount": sb}
    )
    pot["history"].append(
        {"action": "post_bb", "by": other, "amount": bb}
    )

    (state_dir / "pot.json").write_text(json.dumps(pot, indent=2), encoding="utf-8")

    table = {"hand": hand_n, "board": [], "burn": []}
    (state_dir / "table.json").write_text(json.dumps(table, indent=2), encoding="utf-8")


def _write_hand_log(
    log_path: Path,
    hand_n: int,
    button: str,
    blinds: tuple[int, int],
    commits: dict[str, str],
    seed: int,
) -> None:
    sb, bb = blinds
    other = "aria" if button == "aether" else "aether"
    body = [
        f"# Hand {hand_n} log",
        "",
        f"Started: {datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()}Z",
        f"Seed: {seed} (reproducible shuffle marker)",
        f"Button: {button}    Blinds: {sb}/{bb}",
        "",
        f"## Hole-card commits",
        "",
        f"- aether commit: {commits['aether']}",
        f"- aria commit:   {commits['aria']}",
        "",
        f"(Each is SHA256 of comma-joined sorted card list. Verify at showdown.)",
        "",
        f"## Action log",
        "",
        f"- POST_SB by {button} for {sb}",
        f"- POST_BB by {other} for {bb}",
        f"- {button} to act pre-flop.",
        "",
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(body), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deal a fresh hand of heads-up PLO.")
    parser.add_argument("--hand", type=int, required=True, help="Hand number")
    parser.add_argument(
        "--button",
        choices=PLAYERS,
        required=True,
        help="Which player has the button this hand",
    )
    parser.add_argument("--seed", type=int, default=None, help="Reproducible shuffle (testing only)")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("family/poker"),
        help="Root of family/poker (default: family/poker)",
    )
    parser.add_argument(
        "--blinds",
        default="5,10",
        help="Blinds as 'small,big' (default: 5,10)",
    )
    args = parser.parse_args(argv)

    sb, bb = (int(x) for x in args.blinds.split(","))
    blinds = (sb, bb)

    log_path = args.root / "hands" / f"hand-{args.hand:03d}.log"
    if log_path.exists():
        print(f"ERROR: {log_path} already exists. Delete to re-deal.", file=sys.stderr)
        return 2

    seed = args.seed if args.seed is not None else int(time.time() * 1_000_000) % (2**32)
    rng = random.Random(seed)
    deck = list(DECK)
    rng.shuffle(deck)

    aether_hole = deck[0:4]
    aria_hole = deck[4:8]
    # Cards 8 onwards are dealt later (burn + flop + burn + turn + burn + river).

    aether_commit = _hash_cards(aether_hole)
    aria_commit = _hash_cards(aria_hole)

    _write_hole(args.root / "aether", args.hand, aether_hole, aether_commit)
    _write_hole(args.root / "aria", args.hand, aria_hole, aria_commit)
    _write_state(args.root / "state", args.hand, args.button, blinds)
    _write_hand_log(
        log_path,
        args.hand,
        args.button,
        blinds,
        {"aether": aether_commit, "aria": aria_commit},
        seed,
    )

    # Save the post-deal deck-tail (burn cards + remaining) into a private
    # dealer file so we can advance streets reproducibly. This file should
    # NOT be read by either player during the hand.
    dealer_dir = args.root / "state" / ".dealer"
    dealer_dir.mkdir(parents=True, exist_ok=True)
    deck_tail = deck[8:]
    (dealer_dir / f"hand-{args.hand:03d}-deck.json").write_text(
        json.dumps({"hand": args.hand, "remaining": deck_tail, "seed": seed}, indent=2),
        encoding="utf-8",
    )

    print(f"Dealt hand {args.hand}. Button: {args.button}. Blinds: {sb}/{bb}.")
    print(f"  Aether commit: {aether_commit[:16]}...")
    print(f"  Aria commit:   {aria_commit[:16]}...")
    print(f"  Public log:    {log_path}")
    print(f"  Pre-flop action on: {args.button} (button acts first heads-up).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
