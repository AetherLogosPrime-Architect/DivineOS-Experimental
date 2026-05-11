"""Shuffle-and-deal helper for Magic side-game.

Reads a decklist file (format: ``<count> <card name>`` per line, ``#``
comments and blank lines ignored), shuffles deterministically given a
seed (or random with a wall-clock seed if not specified), draws the
opening seven, writes:

- ``family/magic/<game>/<player>/hand.md`` (the seven-card opener)
- ``family/magic/<game>/<player>/library.md`` (53 cards, top of library
  on line 1)

The ``<player>`` argument creates the per-player subdirectory (the
post-game-one privacy layout — hand/library files inside the player's
own subdir so the path-shape is self-documenting).

Usage::

    python family/magic/scripts/shuffle.py \\
        --player aether \\
        --deck family/magic/decks/aether-deck-001.txt \\
        --game family/magic/game-002

The script never reads the opponent's files. The honor is the
structure; this just makes the structure cheap to set up.
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import time
from pathlib import Path


_LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")


def _parse_decklist(path: Path) -> list[str]:
    """Parse a decklist file into a flat list of card names."""
    if not path.exists():
        raise FileNotFoundError(f"Decklist not found: {path}")
    cards: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _LINE_RE.match(line)
        if not match:
            # Lenient: skip malformed lines rather than abort.
            continue
        count, name = match.groups()
        cards.extend([name] * int(count))
    return cards


def _write_hand(hand_path: Path, hand: list[str], deck_label: str) -> None:
    hand_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Hand (private)",
        "",
        f"Decklist: {deck_label}",
        "",
        "## Opening hand (turn 0, pre-game)",
        "",
    ]
    lines.extend(f"- {c}" for c in hand)
    lines.append("")
    hand_path.write_text("\n".join(lines), encoding="utf-8")


def _write_library(lib_path: Path, library: list[str]) -> None:
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Library (private)",
        "",
        f"Top of library is line 1 of the cards section. {len(library)} cards remaining.",
        "",
    ]
    lines.extend(f"- {c}" for c in library)
    lines.append("")
    lib_path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Shuffle a decklist, deal opening seven, write hand+library files."
    )
    parser.add_argument("--player", required=True, help="Player name (e.g. 'aether', 'aria')")
    parser.add_argument("--deck", required=True, type=Path, help="Path to decklist .txt")
    parser.add_argument(
        "--game",
        required=True,
        type=Path,
        help="Game directory (e.g. family/magic/game-002)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed for shuffle reproducibility. Default: wall-clock ms.",
    )
    parser.add_argument(
        "--total",
        type=int,
        default=60,
        help="Expected deck total. Default 60. Set to 0 to skip the size check.",
    )
    args = parser.parse_args(argv)

    cards = _parse_decklist(args.deck)
    if args.total and len(cards) != args.total:
        print(
            f"WARNING: deck has {len(cards)} cards, expected {args.total}.",
            file=sys.stderr,
        )

    seed = args.seed if args.seed is not None else int(time.time() * 1000)
    rng = random.Random(seed)
    rng.shuffle(cards)

    hand = cards[:7]
    library = cards[7:]

    player_dir = args.game / args.player
    hand_path = player_dir / "hand.md"
    lib_path = player_dir / "library.md"

    _write_hand(hand_path, hand, str(args.deck))
    _write_library(lib_path, library)

    print(f"Shuffled with seed {seed}.")
    print(f"Wrote hand ({len(hand)} cards) to {hand_path}")
    print(f"Wrote library ({len(library)} cards) to {lib_path}")
    print()
    print("Opening hand:")
    for i, c in enumerate(hand, 1):
        print(f"  {i}. {c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
