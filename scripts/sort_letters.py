"""Sort the letter corpus into boxes. Re-runnable, additive, filename-driven.

Andrew 2026-07-31: "all the letters need sorted into their own boxes.. personal
letters vs work or any other categories you need for easier navigation
otherwise its just a giant pile of letters lol"

WHY THIS SCRIPT IS IN THE REPO
------------------------------
A sort already ran on 2026-07-09. Its SORT_LOG.md still sits in the shared
folder; the folders it created are gone and the pile is flat again. That sort
was a throwaway, run once and never committed, so the corpus re-piled and
nobody could re-run the fix. This one lives in scripts/ and is idempotent —
running it twice is the same as running it once.

FOLDERS VS TAGS, and why the split falls where it does
------------------------------------------------------
Andrew 2026-07-31: "keyword detectors are not a sin.. IF they are used in the
appropriate manner.. keyword ENFORCEMENT is forbidden. keywords for searching
and retrieval is fine."

That draws the line this script is built on:

  * A wrong FOLDER hides a letter. Folders are exclusive and a misfile is
    silent — you find out only when you go looking and it isn't there.
  * A wrong TAG adds noise to a search. Additive, and cheap to be wrong about.

So folders carry only what is CERTAIN: who wrote to whom, and when. That reads
straight off the filename for 98% of the corpus (1468/1495) with no guessing.

Topic belongs in tags, where being wrong costs nothing — and that job is
already done by scripts/classify_letters.py, which writes a reviewable
INDEX.md rather than moving anything. Its own docstring says "I review by hand
for surprises," which is retrieval-with-a-human-check, exactly the use Andrew
named as fine. The two compose: this script makes the boxes, that one makes
the index. Neither enforces anything.

This also answers "personal vs work" from fact rather than word-counting:
the correspondent IS the category. aether<->aria is the marriage.
aether<->aletheia is audit work.

THE INBOX STAYS FLAT
--------------------
New letters land flat at the top level, which is exactly where the letter
monitor looks (top-level glob only). Filing the backlog into subfolders
therefore does not blind the watcher. Re-run this whenever the inbox fills.

Nothing is deleted; every operation is a move inside the letters tree, logged
to SORT_LOG.md. The full pre-sort corpus is archived outside both workspaces
at C:/DIVINE OS/_letter_archive_2026-07-31/.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SHARED = Path(r"C:/Users/aethe/.divineos-shared/letters")

# Never move these — they are the folder's own furniture.
KEEP_FLAT = {"README.md", "INDEX.md", "SORT_LOG.md"}

# <sender>-to-<recipient>-<YYYY-MM-DD>-<slug>.md — the certain case.
PAIR_RE = re.compile(r"^(?P<a>[a-z]+)-to-(?P<b>[a-z]+(?:-[a-z]+)?)-(?P<date>\d{4}-\d{2}-\d{2})")
SELFLOG_RE = re.compile(r"^(?P<who>[a-z]+)-(?:self-log|feelings-log|notes)-")
NUMBERED_RE = re.compile(r"^\d+[_-]")


def destination(name: str) -> tuple[Path, str] | None:
    """Return (relative destination dir, rule name), or None to leave flat."""
    if name in KEEP_FLAT:
        return None

    if NUMBERED_RE.match(name):
        return Path("archive/numbered-legacy"), "numbered-legacy"

    m = SELFLOG_RE.match(name)
    if m:
        return Path("self-logs") / m["who"], "self-log"

    m = PAIR_RE.match(name)
    if m:
        # Normalize the pair so both directions land in ONE thread folder.
        # Without this, aether-to-aria and aria-to-aether become two piles of
        # half a conversation each — which is the problem, not the fix.
        a, b = sorted((m["a"], m["b"]))
        return Path("threads") / f"{a}-{b}" / m["date"][:7], "correspondence"

    return Path("archive/unparsed"), "unparsed"


def plan(root: Path) -> list[tuple[Path, Path, str]]:
    moves = []
    for f in sorted(root.glob("*.md")):
        d = destination(f.name)
        if d is None:
            continue
        rel, rule = d
        moves.append((f, root / rel / f.name, rule))
    return moves


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move files")
    ap.add_argument("--root", default=str(SHARED))
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"No such letters dir: {root}")
        return 1

    moves = plan(root)
    if not moves:
        print(f"Inbox is clear — nothing at the top level of {root} needs filing.")
        return 0

    by_rule = Counter(rule for _, _, rule in moves)
    by_box = Counter(str(dst.parent.relative_to(root)) for _, dst, _ in moves)

    print(f"{'APPLY' if args.apply else 'DRY RUN'} — {len(moves)} letters to file\n")
    print("by rule:")
    for rule, n in by_rule.most_common():
        print(f"  {rule:16} {n}")
    print(f"\ntop boxes (of {len(by_box)} total):")
    for box, n in by_box.most_common(12):
        print(f"  {box:36} {n}")

    if not args.apply:
        print("\nNothing moved. Re-run with --apply.")
        return 0

    log_lines = [f"\n## Sort run — {datetime.now(timezone.utc).isoformat()}\n"]
    moved = collided = 0
    for src, dst, rule in moves:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            # Never overwrite. A same-named file already in the box is left
            # alone, and this one stays in the inbox for a human to look at.
            log_lines.append(f"- SKIP `{src.name}` -> `{dst}` (already present)")
            collided += 1
            continue
        shutil.move(str(src), str(dst))
        log_lines.append(f"- MOVE `{src.name}` -> `{dst.relative_to(root)}`  (rule: `{rule}`)")
        moved += 1

    log = root / "SORT_LOG.md"
    with log.open("a", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")

    remaining = len([f for f in root.glob("*.md") if f.name not in KEEP_FLAT])
    print(f"\nmoved: {moved}   skipped (name already in box): {collided}")
    print(f"inbox now holds {remaining} unfiled letters")
    print(f"log appended to {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
