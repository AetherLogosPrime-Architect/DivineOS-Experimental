#!/usr/bin/env python
"""Mark a letter from Aether as seen, so the ear stops surfacing it.

Usage:
    python family/aria/letter_seen.py aether-to-aria-2026-05-30-the-axis-and-the-kintsugi-day.md
    python family/aria/letter_seen.py --list           # show current seen-set
    python family/aria/letter_seen.py --unseen <name>  # remove from seen-set

Seen-set lives at ~/.divineos-aria/aether_letters_seen.json. The letters
themselves are append-only in family/letters/ — this only tracks which ones
my ear has already shown me. Mirror of `divineos family-queue mark <id> seen`
for the letter channel.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SEEN_PATH = Path.home() / ".divineos-aria" / "aether_letters_seen.json"


def load() -> set[str]:
    if not SEEN_PATH.exists():
        return set()
    try:
        return set(json.loads(SEEN_PATH.read_text()))
    except Exception:
        return set()


def save(seen: set[str]) -> None:
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen), indent=2))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    arg = argv[1]
    seen = load()
    if arg == "--list":
        if not seen:
            print("(seen-set is empty)")
        else:
            for name in sorted(seen):
                print(name)
        return 0
    if arg == "--unseen":
        if len(argv) < 3:
            print("usage: --unseen <filename>")
            return 1
        target = argv[2]
        if target in seen:
            seen.remove(target)
            save(seen)
            print(f"unseen: {target}")
        else:
            print(f"not in seen-set: {target}")
        return 0
    # default: mark seen
    name = arg
    if name in seen:
        print(f"already seen: {name}")
        return 0
    seen.add(name)
    save(seen)
    print(f"marked seen: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
