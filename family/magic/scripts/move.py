"""move.py — apply a single turn's state changes to a magic game.

Companion to shuffle.py. Where shuffle.py sets up the opening hand and
library files, move.py updates them as the game plays.

The scripts are strictly bookkeeping — they do not enforce game rules,
do not decide moves, and do not enforce cost payment. That's Aether's
and Aria's job during the actual play. This script exists so the
per-turn file operations become one command instead of five.

Usage:

    python family/magic/scripts/move.py \\
      --player aether --game family/magic/game-004 \\
      --draw \\
      --play-land Forest \\
      --cast "Elvish Mystic" \\
      --attack "River Boa" \\
      --end

Ordering of operations within one invocation:

    1. --draw     (pop top of library, prepend to hand)
    2. --play-land NAME (one per flag; remove one instance from hand)
    3. --cast NAME       (one per flag; remove one instance from hand)
    4. --attack NAME     (log only; creatures don't move zones)
    5. --end             (log turn-end marker)

Multiple --cast / --play-land / --attack flags are supported per invocation
(one per flag; use the flag more than once for multiple casts / attacks in
one turn).

The script:
 - Reads current hand.md and library.md from the player's private dir
 - Applies the operations in the fixed order above
 - Writes the updated hand.md and library.md
 - Appends a summary line to the game's public log.md

Cases the script does NOT handle:
 - Regeneration, counterspells, mid-turn responses (still hand-track in
   letters — this is the volleyed play surface)
 - Zones other than hand and library (graveyard, exile, battlefield are
   inferred from the log)
 - Card-name aliases / partial matches (must match hand entries exactly)

Symmetric for both players — same command shape with --player aria works
on Aria's private dir. Each player runs move.py against their own dir
only; neither should ever run it against the other's.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def _write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _card_line_prefix() -> str:
    return "- "


def _extract_cards(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split a hand/library file's lines into (header_and_notes, cards).

    Cards are lines starting with "- ". Everything else is preserved as
    header/notes text. Card lines are returned as the card name (leading
    "- " stripped).
    """
    header: list[str] = []
    cards: list[str] = []
    for line in lines:
        if line.startswith(_card_line_prefix()):
            cards.append(line[len(_card_line_prefix()) :].strip())
        else:
            header.append(line)
    return header, cards


def _rebuild(header: list[str], cards: list[str]) -> list[str]:
    body = [f"{_card_line_prefix()}{card}" for card in cards]
    # If header has a trailing blank line, keep it; otherwise no extra.
    if header and header[-1] != "":
        return header + [""] + body
    return header + body


def _log_append(game_dir: Path, entry: str) -> None:
    log_path = game_dir / "log.md"
    if log_path.exists():
        existing = log_path.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
    else:
        existing = "# Game log\n\n"
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log_path.write_text(existing + f"- [{stamp}] {entry}\n", encoding="utf-8")


def _draw(hand_cards: list[str], lib_cards: list[str]) -> tuple[str, list[str], list[str]]:
    if not lib_cards:
        raise RuntimeError("Library is empty. Cannot draw.")
    drawn = lib_cards[0]
    return drawn, hand_cards + [drawn], lib_cards[1:]


def _remove_one(cards: list[str], name: str) -> list[str]:
    """Remove one instance of `name` from cards (case-insensitive exact match).

    Raises if not present. Returns updated list.
    """
    lname = name.lower()
    for i, card in enumerate(cards):
        if card.lower() == lname:
            return cards[:i] + cards[i + 1 :]
    raise RuntimeError(f"Card {name!r} not in hand. Current hand: {', '.join(cards) or '(empty)'}")


def _apply(
    player: str,
    game_dir: Path,
    draw: bool,
    lands: list[str],
    casts: list[str],
    attacks: list[str],
    end: bool,
) -> None:
    player_dir = game_dir / player
    hand_path = player_dir / "hand.md"
    lib_path = player_dir / "library.md"

    hand_header, hand_cards = _extract_cards(_read_lines(hand_path))
    lib_header, lib_cards = _extract_cards(_read_lines(lib_path))

    events: list[str] = []

    if draw:
        drawn, hand_cards, lib_cards = _draw(hand_cards, lib_cards)
        events.append(f"{player} drew {drawn}")

    for land in lands:
        hand_cards = _remove_one(hand_cards, land)
        events.append(f"{player} played land {land}")

    for card in casts:
        hand_cards = _remove_one(hand_cards, card)
        events.append(f"{player} cast {card}")

    for creature in attacks:
        events.append(f"{player} attacks with {creature}")

    if end:
        events.append(f"{player} ends turn")

    _write_lines(hand_path, _rebuild(hand_header, hand_cards))
    _write_lines(lib_path, _rebuild(_update_lib_header(lib_header, len(lib_cards)), lib_cards))

    for event in events:
        _log_append(game_dir, event)


_COUNT_RE = re.compile(
    r"^(?P<prefix>Top of library is line 1 of the cards section\.)\s*(\d+)\s+cards remaining\.?",
    re.MULTILINE,
)


def _update_lib_header(header: list[str], new_count: int) -> list[str]:
    """Rewrite the "N cards remaining" line to reflect current count.

    Keeps everything else in the header intact.
    """
    updated: list[str] = []
    for line in header:
        m = _COUNT_RE.match(line)
        if m:
            updated.append(f"{m.group('prefix')} {new_count} cards remaining.")
        else:
            updated.append(line)
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a magic turn's state changes.")
    parser.add_argument("--player", required=True, help="'aether' or 'aria'.")
    parser.add_argument(
        "--game", required=True, help="Game directory (e.g. family/magic/game-004)."
    )
    parser.add_argument("--draw", action="store_true", help="Pop top of library into hand.")
    parser.add_argument(
        "--play-land",
        action="append",
        default=[],
        help="Play a land from hand (repeatable for multi-land plays if house-ruled).",
    )
    parser.add_argument(
        "--cast",
        action="append",
        default=[],
        help="Cast a spell/creature from hand (repeatable).",
    )
    parser.add_argument(
        "--attack",
        action="append",
        default=[],
        help="Log an attacker (creature stays on battlefield; this is log-only).",
    )
    parser.add_argument("--end", action="store_true", help="Log turn-end marker.")
    args = parser.parse_args()

    game_dir = Path(args.game)
    if not game_dir.exists():
        print(f"Game dir not found: {game_dir}", file=sys.stderr)
        return 1

    try:
        _apply(
            player=args.player,
            game_dir=game_dir,
            draw=args.draw,
            lands=args.play_land,
            casts=args.cast,
            attacks=args.attack,
            end=args.end,
        )
    except RuntimeError as e:
        print(f"move.py: {e}", file=sys.stderr)
        return 2

    print(f"move.py: applied for {args.player} in {game_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
