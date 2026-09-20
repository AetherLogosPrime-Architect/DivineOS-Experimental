#!/usr/bin/env python3
"""Refuse two source files with byte-identical content.

WHAT IT COST, 2026-09-20. A 488-line module existed twice under the same name,
in two directories, byte for byte the same -- same length, same hash. One copy
was live: every test imported it and the audit path called it. The other had no
caller, no test, and nothing unique in it, and it sat there for a month.

NOTHING SAW IT, and the reason is the shape of the whole day. The orphan
checker asks about modules that HAVE TESTS and no caller; this one had no
tests, so it was outside the question by construction rather than by neglect.
It surfaced only because a sweep for repeated PROSE noticed forty-two identical
comment lines across two paths, which is a coincidence rather than a method.

The duplicate arrived in a refactor whose own title was about instruments that
could not say whose session they were reading. That detail stays because it is
the lesson in miniature: a copy made while tidying is invisible to the person
tidying, and correct from where they stand.

NOT THE FIRST TIME IN A DIFFERENT COSTUME. check_referenced_paths records two
byte-identical commits with the same message on two branches, found by hand in
August. Same class, no check, so it came back wearing a module instead.

WHY BYTE-IDENTICAL RATHER THAN SIMILAR. Near-duplicate detection needs a
threshold, a threshold needs tuning, and a tuned number is something people
argue with instead of a fact. Identical is a fact. It under-reports on purpose
-- two files one line apart are not caught -- and what it does report is never
a judgement call, which is what makes it safe to have block.

LEGITIMATE IDENTICAL FILES EXIST and get named rather than guessed at: empty
markers, generated stubs, vendored copies. Say so with
`# duplicate-by-design: <why>` inside the file and this stands aside.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_SEARCH_ROOTS = ("src", "scripts", ".claude/hooks")
_SUFFIXES = (".py", ".sh")

# ANY-DEPTH skips: these directories are never source, wherever they appear.
_SKIP_ANYWHERE = {".venv", "__pycache__", "node_modules"}

# TOP-LEVEL-ONLY skips, and the distinction was earned immediately. The first
# version skipped any path containing a part named "tmp", which silently
# excluded every file this check's own tests handed it, because the test
# scratch directory sits under a folder of that name. The check reported clean
# on a tree containing nothing but the duplicate it was built to find.
#
# That is the fake-green shape again, inside the file written against a blind
# spot, and it was caught by the positive case failing rather than by reading.
# Scoped to the repository root now, where "this is scratch, not source" is
# actually true.
_SKIP_AT_ROOT = {"worktrees", "tmp", "build", "dist"}

_ESCAPE = "# duplicate-by-design:"

# Below this, identical content is ordinary rather than suspicious: a one-line
# re-export or an empty package marker says nothing worth saying twice.
_MIN_BYTES = 400


def _candidates() -> list[Path]:
    out: list[Path] = []
    for root in _SEARCH_ROOTS:
        base = REPO / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix not in _SUFFIXES or not p.is_file():
                continue
            if _SKIP_ANYWHERE & set(p.parts):
                continue
            try:
                first = p.relative_to(REPO).parts[0]
            except ValueError:
                first = ""
            if first in _SKIP_AT_ROOT:
                continue
            out.append(p)
    return out


def find_duplicates() -> list[tuple[str, list[str]]]:
    by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in _candidates():
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) < _MIN_BYTES or _ESCAPE.encode() in data:
            continue
        by_hash[hashlib.sha256(data).hexdigest()].append(path)

    found: list[tuple[str, list[str]]] = []
    for digest, paths in sorted(by_hash.items()):
        if len(paths) < 2:
            continue
        found.append(
            (
                digest[:12],
                sorted(str(p.relative_to(REPO)).replace("\\", "/") for p in paths),
            )
        )
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="Refuse byte-identical source files.")
    ap.add_argument("--warn-only", action="store_true", help="print findings and exit 0")
    args = ap.parse_args()

    candidates = _candidates()
    if not candidates:
        # Nothing scanned is not the same as nothing found, and the difference
        # is the entire subject of this file.
        print(
            "[duplicate-files] NO FILES WERE SCANNED, so nothing was checked. "
            "This exit is not a pass.",
            file=sys.stderr,
        )
        return 0 if args.warn_only else 1

    dupes = find_duplicates()
    if not dupes:
        print(f"[duplicate-files] no byte-identical files among {len(candidates)} scanned.")
        return 0

    print(f"[duplicate-files] {len(dupes)} set(s) of byte-identical files:\n", file=sys.stderr)
    for digest, paths in dupes:
        print(f"  identical ({digest}):", file=sys.stderr)
        for p in paths:
            print(f"      {p}", file=sys.stderr)
    print(
        "\nOne of these is probably reachable and the others are not. TRACE THE\n"
        "CALLERS before removing anything -- the live copy is not reliably the\n"
        "one in the more obvious directory, and it was not last time. If the\n"
        "duplication is deliberate, say why in the file with\n"
        "`# duplicate-by-design: <reason>`.",
        file=sys.stderr,
    )
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    raise SystemExit(main())
