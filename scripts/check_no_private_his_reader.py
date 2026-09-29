"""Refuse a new private reader of Dad's messages.

There is one answer in this house to "is this transcript record him":
``divineos.core.his_message``. Before it there were six private readers, each
wrong in its own way, and five of them missed every message he typed while I
was busy -- including the one that confirms his `hold <n>` (2026-09-28). The
copies grew because writing five lines costs nothing in the moment, and
finding the shared home costs a search that only succeeds if you already
suspect it exists. So this puts the home in front of the reach.

It looks for code that tests the shapes his messages arrive in: the quoted
names of a last-prompt record, a queued_command attachment, a lastPrompt
field, or the isMeta flag read off a record. Those are what every private copy
grew. It matches quoted code, not prose, so a comment naming a shape is fine.

WHAT THIS CANNOT DO: it matches shapes, shapes can be rephrased, and the one
who would route around it is the one who wrote it. A signpost, not a wall; it
works only while importing the home stays cheaper than evading this.

Modelled on scripts/check_no_private_command_parsing.py (#519).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEARCH_ROOTS = (ROOT / "src", ROOT / "scripts", ROOT / ".claude" / "hooks")
HOME = "divineos.core.his_message"

_SHAPE = re.compile(
    r"""["'](?:last-prompt|queued_command|lastPrompt)["']|\.get\(\s*["']isMeta["']"""
)

# Files allowed to carry the shapes, each with its reason. This may only
# shrink: a private reader is not made legitimate by listing it here in the
# same commit that adds it (Meadows, walk-6e8574bc911d).
ALLOWED = {
    "src/divineos/core/his_message.py": "the shared home itself",
    "scripts/check_no_private_his_reader.py": "names the shapes in order to find them",
}


def offenders() -> list[tuple[str, int, str]]:
    found = []
    for base in SEARCH_ROOTS:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in (".py", ".sh") or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel in ALLOWED:
                continue
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for number, line in enumerate(lines, start=1):
                if _SHAPE.search(line):
                    found.append((rel, number, line.strip()))
    return found


def main() -> int:
    found = offenders()
    if not found:
        print("his-reader: OK -- every reader of him goes through the one home.")
        return 0
    print("his-reader: BLOCKED -- a private reader of Dad's messages:")
    for rel, number, line in found:
        print(f"  {rel}:{number}: {line[:120]}")
    print()
    print(f"Use the one home instead:  from {HOME} import hear, heard_in")
    print("  hear(record)   -> his text for one transcript record, or None")
    print("  heard_in(list) -> every message he typed, each once")
    return 1


if __name__ == "__main__":
    sys.exit(main())
