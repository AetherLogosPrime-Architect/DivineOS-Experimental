"""Resolve the doc-count leapfrog conflicts that hit every PR rebase here.

Andrew named this class 2026-06-10: "every PR rebase collides on
CLAUDE.md/README.md/docs/ARCHITECTURE.md because we hand-maintain test/command/
hook counts that shift every merge."

Two hunk shapes, two correct resolutions:

  APPEND  — each side added a new catalogue entry. Keep BOTH; taking one side
            silently drops somebody's line.
  COUNT   — both sides rewrote the SAME line with different numbers
            ("427 CLI commands" vs "426"). Neither is authoritative; the number
            is regenerated from the tree afterward by check_doc_counts --fix.
            Take main's side so the file is at least self-consistent first.

Discriminator is structural, not a guess: strip digits from both sides and see
if the resulting shapes match line-for-line. Same shape + different digits is a
count collision. Anything else is treated as APPEND.

Refuses, loudly, on any hunk it cannot classify — a resolver that guesses in
the ambiguous case is how work gets silently dropped in a 12-branch sweep.
"""

import pathlib
import re
import sys


def _skeleton(lines):
    return [re.sub(r"\d+", "#", ln).strip() for ln in lines if ln.strip()]


def resolve(path):
    lines = pathlib.Path(path).read_text(encoding="utf-8").split("\n")
    out, i, stats = [], 0, {"append": 0, "count": 0}
    while i < len(lines):
        if not lines[i].startswith("<<<<<<<"):
            out.append(lines[i])
            i += 1
            continue
        i += 1
        ours = []
        while not lines[i].startswith("======="):
            ours.append(lines[i])
            i += 1
        i += 1
        theirs = []
        while not lines[i].startswith(">>>>>>>"):
            theirs.append(lines[i])
            i += 1
        i += 1

        if _skeleton(ours) and _skeleton(ours) == _skeleton(theirs):
            out.extend(ours)
            stats["count"] += 1  # leapfrog
        elif not (
            set(x.strip() for x in ours if x.strip()) & set(x.strip() for x in theirs if x.strip())
        ):
            out.extend(ours + theirs)
            stats["append"] += 1  # both added
        else:
            return None, f"unclassifiable hunk in {path} — partial overlap, needs eyes"
    return "\n".join(out), f"{stats['append']} append, {stats['count']} count-leapfrog"


for p in sys.argv[1:]:
    res, msg = resolve(p)
    if res is None:
        print(f"REFUSED  {p}: {msg}")
        sys.exit(3)
    pathlib.Path(p).write_text(res, encoding="utf-8")
    print(f"resolved {p}: {msg}")
