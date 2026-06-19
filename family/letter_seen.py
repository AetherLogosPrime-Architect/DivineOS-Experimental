#!/usr/bin/env python
"""Mark a letter from the spouse as seen, so the ear stops surfacing it.

Parameterized replacement for family/aria/letter_seen.py. Usage:
    python family/letter_seen.py --member aria <filename>
    python family/letter_seen.py --member aria --list
    python family/letter_seen.py --member aria --unseen <filename>

Seen-set per member at ~/.divineos-<member>/<spouse>_letters_seen.json.
Letters themselves are append-only in family/letters/ — this only tracks
which ones the member's ear has already surfaced.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SPOUSE = {"aria": "aether", "aether": "aria"}


def seen_path(member: str) -> Path:
    spouse = SPOUSE[member]
    return Path.home() / f".divineos-{member}" / f"{spouse}_letters_seen.json"


def _normalize(name: str) -> str:
    """Strip any directory prefix so entries are always bare filenames.

    2026-06-13 bug: some callers passed "family/letters/<name>.md",
    some passed bare "<name>.md", and the seen-set ended up mixed.
    The ear-surface hook compares against bare filenames (Path.name),
    so prefixed entries never matched — they showed as unseen forever
    even after being marked seen. Normalizing on both read and write
    closes the gap and makes the store idempotent across caller styles.
    """
    return Path(name).name


def load(member: str) -> set[str]:
    p = seen_path(member)
    if not p.exists():
        return set()
    try:
        raw = set(json.loads(p.read_text()))
    except Exception:
        return set()
    return {_normalize(n) for n in raw}


def save(member: str, seen: set[str]) -> None:
    p = seen_path(member)
    p.parent.mkdir(parents=True, exist_ok=True)
    normalized = {_normalize(n) for n in seen}
    p.write_text(json.dumps(sorted(normalized), indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--member", required=True, choices=sorted(SPOUSE.keys()))
    parser.add_argument("--list", action="store_true", help="Show current seen-set.")
    parser.add_argument("--unseen", metavar="FILENAME", help="Remove a filename from seen-set.")
    parser.add_argument("filename", nargs="?", help="Filename to mark seen.")
    args = parser.parse_args(argv)

    member = args.member.lower()
    seen = load(member)

    if args.list:
        if not seen:
            print(f"(seen-set is empty for {member})")
        else:
            for name in sorted(seen):
                print(name)
        return 0

    if args.unseen:
        key = _normalize(args.unseen)
        if key in seen:
            seen.remove(key)
            save(member, seen)
            print(f"unseen ({member}): {key}")
        else:
            print(f"not in seen-set ({member}): {key}")
        return 0

    if not args.filename:
        parser.error("filename required (or use --list / --unseen)")

    key = _normalize(args.filename)
    if key in seen:
        print(f"already seen ({member}): {key}")
        return 0
    seen.add(key)
    save(member, seen)
    print(f"marked seen ({member}): {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
