"""The arrival exam for a FILE: does the memory link bring it back from a situation, and if not, why not.

Usage:  python self_arrival_exam.py cases.json
cases.json is a list of {"file": "<path from the repo root or absolute>", "situation": "<words of a moment>"}.
The situations must be phrased by the OTHER seat (a wording taken from the file's own opening always matches it).

Read-only. For each case it says one of three things, because they need three different fixes:
  NOT INDEXED        no lane holds this file at all: a source adapter is missing (the folder is not read)
  INDEXED, NOT SHOWN the file is in a lane but did not pass the bar for this situation: a ranking or wording gap
  ARRIVED            it passed the bar for this situation (the lane, the rank and the similarity are printed)

How a file is recognised is by identity, not by judging its words: the lane item's id or title carries the
file's stem, or the item's first line is the file's first line. That match only CONFIRMS which file arrived;
it decides nothing about the file's meaning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from divineos.core import memory_linkage_retriever_v2 as v


def first_line(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            return line.strip()
    return ""


def is_this_file(item, stem: str, fingerprint: str) -> bool:
    ident = f"{getattr(item, 'id', '')} {getattr(item, 'title', '')}"
    if stem and stem in ident:
        return True
    content = str(getattr(item, "content", "")).lstrip()
    return bool(fingerprint) and content.startswith(fingerprint[:80])


def main(cases_path: str) -> int:
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    v._ensure_v2_state()
    failures = 0
    for case in cases:
        path = Path(case["file"])
        if not path.is_file():
            print(f"COULD NOT LOOK   {case['file']}: no such file (not the same as 'not indexed')")
            failures += 1
            continue
        stem, fp = path.stem, first_line(path)
        held = [
            (source, item)
            for source, items in v._EMBEDDING_CACHE.items()
            for item in items
            if is_this_file(item, stem, fp)
        ]
        rows = v.explain_turn(case["situation"])
        arrived = [
            (r["source"], row)
            for r in rows
            for row in r["rows"]
            if row["passed"] and (stem in str(row["id"]) or stem in str(row["title"]))
        ]
        if arrived:
            src, row = arrived[0]
            print(f"ARRIVED          {case['file']}  [{src}] score {row['rank']:.2f} sim {row['similarity']:.2f}")
        elif held:
            failures += 1
            print(
                f"INDEXED, NOT SHOWN  {case['file']}  held by {sorted({s for s, _ in held})}; "
                "this situation did not carry it over the bar"
            )
        else:
            failures += 1
            print(f"NOT INDEXED      {case['file']}  no lane holds it (a source adapter for its folder is missing)")
    print(f"{len(cases)} cases, {failures} not arrived")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
