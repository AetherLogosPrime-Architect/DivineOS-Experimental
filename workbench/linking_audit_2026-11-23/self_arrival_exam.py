"""The arrival exam for a FILE: does the memory link bring it back from a situation, and if not, why not.

Usage:  python self_arrival_exam.py cases.json
cases.json is a list of {"file": "<path from the repo root or absolute>", "situation": "<words of a moment>"}.
The situations must be phrased by the OTHER seat (a wording taken from the file's own opening always matches it).

Read-only. Each file gets exactly one word, and each word is a different repair:
  COULD NOT LOOK      the file could not be opened (not the same as "not indexed")
  NOT INDEXED         no lane's loader asks about this file at all: a source adapter is missing
  NOT EMBEDDED        a loader asks about it but the drawer holds no vector for its text, so the lane skipped it:
                      run `divineos linkage warm` (the lane counts these as a number and never names them)
  INDEXED, NOT SHOWN  the file is in a lane but did not pass the bar for this situation: a ranking or wording gap
  PASSED BUT CUT      it passed the bar and lost the cap across sources (TOTAL_INJECTION_CAP), so it never
                      reached the turn: a competition gap, not a wording one
  ARRIVED             it passed the bar and was surfaced (the lane, the rank and the similarity are printed)

A control rides along: a file must not arrive for ANOTHER case's situation. One that does is too general to
mean anything (the lacquer test), and the exam reports it and fails.

How a file is recognised is by identity, not by judging its words: the lane item's id or title carries the
file's stem, or the item's first line is the file's first line. That match only CONFIRMS which file arrived;
it decides nothing about the file's meaning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORDS = (
    "COULD NOT LOOK",
    "NOT INDEXED",
    "NOT EMBEDDED",
    "INDEXED, NOT SHOWN",
    "PASSED BUT CUT",
    "ARRIVED",
)


def judge(facts: dict[str, bool]) -> str:
    """One word for one file, from facts the exam gathered. Order matters: a file with a vector in a lane
    is never called not-embedded, and a file that passed is never called not-shown."""
    if not facts["exists"]:
        return "COULD NOT LOOK"
    if facts["held"]:
        if facts["passed"] and facts["surfaced"]:
            return "ARRIVED"
        if facts["passed"]:
            return "PASSED BUT CUT"
        return "INDEXED, NOT SHOWN"
    if facts["collected"]:
        return "NOT EMBEDDED"
    return "NOT INDEXED"


def is_pass(word: str) -> bool:
    return word == "ARRIVED"


def cross_arrivals(arrivals: dict[str, set[str]]) -> list[tuple[str, str]]:
    """The negative control. ``arrivals[f]`` is the set of case files that arrived for the situation phrased
    for f. Returns (situation_file, other_file) pairs where a different file arrived for f's situation."""
    found: list[tuple[str, str]] = []
    for situation_file, arrived in arrivals.items():
        for other in sorted(arrived):
            if other != situation_file:
                found.append((situation_file, other))
    return found


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


def collected_texts() -> list[str]:
    """Every text the lane loaders ask the drawer about, the way `linkage warm` learns what to embed.
    A file whose text is here but absent from the cache was asked about and had no vector."""
    from divineos.core import memory_linkage_retriever as r

    loaders = (
        r._load_corrections,
        r._load_knowledge,
        r._load_wall,
        r._load_exploration,
        r._load_letters,
        r._load_worklist,
        r._load_moments,
    )
    r._COLLECTED.clear()
    r._MODE = "collect"
    try:
        for loader in loaders:
            loader()
    finally:
        r._MODE = "drawer"
    texts = list(r._COLLECTED)
    r._COLLECTED.clear()
    return texts


def _file_is_collected(fingerprint: str, texts: list[str]) -> bool:
    if not fingerprint:
        return False
    head = fingerprint[:80]
    return any(head in text[:600] for text in texts)


def main(cases_path: str) -> int:
    from divineos.core import memory_linkage_retriever_v2 as v

    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    v._ensure_v2_state()
    texts = collected_texts()
    stems = {case["file"]: Path(case["file"]).stem for case in cases}
    arrivals: dict[str, set[str]] = {}
    failures = 0
    for case in cases:
        path = Path(case["file"])
        exists = path.is_file()
        stem = stems[case["file"]]
        fp = first_line(path) if exists else ""
        held = [
            (source, item)
            for source, items in v._EMBEDDING_CACHE.items()
            for item in items
            if exists and is_this_file(item, stem, fp)
        ]
        rows = v.explain_turn(case["situation"]) if exists else []
        mine = [
            (r["source"], row)
            for r in rows
            for row in r["rows"]
            if row["passed"] and (stem in str(row["id"]) or stem in str(row["title"]))
        ]
        facts = {
            "exists": exists,
            "held": bool(held),
            "collected": exists and _file_is_collected(fp, texts),
            "passed": bool(mine),
            "surfaced": any(row.get("surfaced") for _, row in mine),
        }
        word = judge(facts)
        arrived_here = {
            other
            for other, other_stem in stems.items()
            if any(
                row["passed"]
                and row.get("surfaced")
                and (other_stem in str(row["id"]) or other_stem in str(row["title"]))
                for r in rows
                for row in r["rows"]
            )
        }
        arrivals[case["file"]] = arrived_here
        if not is_pass(word):
            failures += 1
        detail = ""
        if mine:
            src, row = mine[0]
            detail = f" [{src}] score {row['rank']:.2f} sim {row['similarity']:.2f}"
        elif word == "INDEXED, NOT SHOWN":
            detail = f" held by {sorted({s for s, _ in held})}; this situation did not carry it over the bar"
        print(f"{word:<19}  {case['file']}{detail}")
    crossed = cross_arrivals(arrivals)
    for situation_file, other in crossed:
        print(
            f"CROSS-ARRIVAL       {other} also arrived for the situation phrased for {situation_file}"
        )
    print(f"{len(cases)} cases, {failures} not arrived, {len(crossed)} cross-arrivals")
    return 1 if failures or crossed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
