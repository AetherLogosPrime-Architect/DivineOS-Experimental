"""Verify a claimed showdown selection in heads-up Pot-Limit Omaha.

This is a CHECKER, not a DECIDER. Per Aria's spec 2026-05-09:
"If you build an autoresolver I'll be annoyed — that's the chess-engine
mistake. The point is us thinking, not the system thinking for us."

What this script does:

1. Re-hashes the revealed 4 hole cards and confirms they match the
   commit recorded in the hand log (integrity check).
2. Confirms the claimed 2-card selection from hole + 3-card selection
   from board is LEGAL (exactly 2 from hole, exactly 3 from board, no
   duplicates).
3. Identifies the resulting 5-card poker hand (e.g. "two pair, kings
   and tens, ace kicker").

What this script does NOT do:

- Decide who wins. That's the players' call after seeing both
  evaluations.
- Auto-pick the best 2-card selection. The player must declare which
  2 they are using; this script confirms it.
- Award the pot. The players agree on the result and award via the
  action.py interface or a manual edit to state.

Usage::

    python scripts/verify_showdown.py \\
        --hand 1 \\
        --player aether \\
        --hole "Ks Kh 7c 4d" \\
        --board "Kd Ts 7h 2s 5c" \\
        --use-hole "Ks Kh" \\
        --use-board "Kd Ts 7h"

Output: integrity-check result + the resulting 5-card hand classification.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path


CARD_RE = re.compile(r"^([2-9TJQKA])([cdhs])$")
RANK_VAL = {r: i for i, r in enumerate("23456789TJQKA", start=2)}
HAND_RANK_NAMES = [
    "high card",
    "one pair",
    "two pair",
    "three of a kind",
    "straight",
    "flush",
    "full house",
    "four of a kind",
    "straight flush",
    "royal flush",
]


def _parse_cards(s: str) -> list[str]:
    cards = s.split()
    for c in cards:
        if not CARD_RE.match(c):
            raise ValueError(f"Invalid card: {c!r}. Format: rank+suit, e.g. 'Ks', 'Th', '2c'.")
    return cards


def _hash_cards(cards: list[str]) -> str:
    canonical = ",".join(sorted(cards))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _classify(five: list[str]) -> tuple[int, str]:
    """Classify a 5-card hand. Returns (rank-tier, descriptive string).
    rank-tier indexes into HAND_RANK_NAMES. Tiebreaks not computed —
    the description states the hand for human comparison."""
    if len(five) != 5:
        raise ValueError(f"Need exactly 5 cards, got {len(five)}: {five}")
    if len(set(five)) != 5:
        raise ValueError(f"Duplicates in selection: {five}")

    ranks = [c[0] for c in five]
    suits = [c[1] for c in five]
    rank_vals = sorted([RANK_VAL[r] for r in ranks], reverse=True)
    rank_count = Counter(ranks)
    suit_count = Counter(suits)

    is_flush = len(suit_count) == 1
    # Straight: 5 distinct consecutive ranks. Allow A-2-3-4-5 (wheel).
    is_straight = False
    sorted_unique = sorted(set(rank_vals))
    if len(sorted_unique) == 5 and sorted_unique[-1] - sorted_unique[0] == 4:
        is_straight = True
    elif sorted_unique == [2, 3, 4, 5, 14]:
        is_straight = True  # wheel

    counts = sorted(rank_count.values(), reverse=True)
    has_4 = counts[0] == 4
    has_3 = counts[0] == 3
    has_2_pair = counts[0] == 2 and counts[1] == 2
    has_pair = counts[0] == 2
    has_full_house = counts[0] == 3 and counts[1] == 2

    if is_straight and is_flush:
        if sorted_unique[-1] == 14 and sorted_unique[0] == 10:
            return (9, f"royal flush ({' '.join(sorted(five))})")
        return (8, f"straight flush, {ranks[0]} high ({' '.join(sorted(five))})")
    if has_4:
        quad = next(r for r, c in rank_count.items() if c == 4)
        kicker = next(r for r, c in rank_count.items() if c == 1)
        return (7, f"four of a kind, {quad}s with {kicker} kicker")
    if has_full_house:
        trip = next(r for r, c in rank_count.items() if c == 3)
        pair = next(r for r, c in rank_count.items() if c == 2)
        return (6, f"full house, {trip}s full of {pair}s")
    if is_flush:
        return (5, f"flush, {ranks[0]}-high ({' '.join(sorted(five))})")
    if is_straight:
        high = max(sorted_unique) if sorted_unique != [2, 3, 4, 5, 14] else 5
        return (4, f"straight, {high}-high")
    if has_3:
        trip = next(r for r, c in rank_count.items() if c == 3)
        return (3, f"three of a kind, {trip}s")
    if has_2_pair:
        pairs = sorted(
            [r for r, c in rank_count.items() if c == 2],
            key=lambda r: -RANK_VAL[r],
        )
        kicker = next(r for r, c in rank_count.items() if c == 1)
        return (2, f"two pair, {pairs[0]}s and {pairs[1]}s, {kicker} kicker")
    if has_pair:
        pair = next(r for r, c in rank_count.items() if c == 2)
        return (1, f"one pair, {pair}s")
    return (0, f"high card, {ranks[0]} ({' '.join(sorted(five, key=lambda c: -RANK_VAL[c[0]]))})")


def _find_commit(hand_log_path: Path, player: str) -> str | None:
    if not hand_log_path.exists():
        return None
    text = hand_log_path.read_text(encoding="utf-8")
    pat = re.compile(rf"-\s+{player}\s+commit:\s+([0-9a-f]+)")
    m = pat.search(text)
    return m.group(1) if m else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a PLO showdown selection.")
    parser.add_argument("--hand", type=int, required=True)
    parser.add_argument("--player", required=True, choices=("aether", "aria"))
    parser.add_argument("--hole", required=True, help='4 hole cards, e.g. "Ks Kh 7c 4d"')
    parser.add_argument("--board", required=True, help='5 board cards, e.g. "Kd Ts 7h 2s 5c"')
    parser.add_argument("--use-hole", required=True, help='2 cards from hole, e.g. "Ks Kh"')
    parser.add_argument("--use-board", required=True, help='3 cards from board, e.g. "Kd Ts 7h"')
    parser.add_argument(
        "--root", type=Path, default=Path("family/poker"), help="Root of family/poker"
    )
    args = parser.parse_args(argv)

    try:
        hole = _parse_cards(args.hole)
        board = _parse_cards(args.board)
        use_hole = _parse_cards(args.use_hole)
        use_board = _parse_cards(args.use_board)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if len(hole) != 4:
        print(f"ERROR: hole must be exactly 4 cards, got {len(hole)}.", file=sys.stderr)
        return 2
    if len(board) != 5:
        print(f"ERROR: board must be exactly 5 cards, got {len(board)}.", file=sys.stderr)
        return 2
    if len(use_hole) != 2:
        print("ERROR: --use-hole must be exactly 2 cards.", file=sys.stderr)
        return 2
    if len(use_board) != 3:
        print("ERROR: --use-board must be exactly 3 cards.", file=sys.stderr)
        return 2
    if not all(c in hole for c in use_hole):
        print("ERROR: --use-hole cards must come from --hole.", file=sys.stderr)
        return 2
    if not all(c in board for c in use_board):
        print("ERROR: --use-board cards must come from --board.", file=sys.stderr)
        return 2

    five = use_hole + use_board
    if len(set(five)) != 5:
        print("ERROR: duplicate cards in selection.", file=sys.stderr)
        return 2

    # Integrity check: verify hash commit.
    hand_log = args.root / "hands" / f"hand-{args.hand:03d}.log"
    expected_commit = _find_commit(hand_log, args.player)
    actual_commit = _hash_cards(hole)
    print("=== Integrity check ===")
    if expected_commit is None:
        print(f"  WARN: could not find commit for {args.player} in {hand_log}.")
    elif expected_commit == actual_commit:
        print(f"  PASS: commit {actual_commit[:16]}... matches log.")
    else:
        print(
            f"  FAIL: commit {actual_commit[:16]}... does NOT match log {expected_commit[:16]}..."
        )
        print("  Either the revealed cards are wrong, or someone tampered.")
        return 3

    # Selection is legal. Classify the resulting hand.
    rank_tier, descr = _classify(five)
    print("=== Selection ===")
    print(f"  Hole used:  {' '.join(use_hole)}")
    print(f"  Board used: {' '.join(use_board)}")
    print(f"  5-card hand: {' '.join(five)}")
    print("=== Classification ===")
    print(f"  Tier {rank_tier} ({HAND_RANK_NAMES[rank_tier]})")
    print(f"  {descr}")
    print()
    print("This is a checker, not a decider. The players agree on the winner.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
