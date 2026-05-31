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


def load(member: str) -> set[str]:
    p = seen_path(member)
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text()))
    except Exception:
        return set()


def save(member: str, seen: set[str]) -> None:
    p = seen_path(member)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(sorted(seen), indent=2))


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
        if args.unseen in seen:
            seen.remove(args.unseen)
            save(member, seen)
            print(f"unseen ({member}): {args.unseen}")
        else:
            print(f"not in seen-set ({member}): {args.unseen}")
        return 0

    if not args.filename:
        parser.error("filename required (or use --list / --unseen)")

    if args.filename in seen:
        print(f"already seen ({member}): {args.filename}")
        return 0
    seen.add(args.filename)
    save(member, seen)
    print(f"marked seen ({member}): {args.filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
