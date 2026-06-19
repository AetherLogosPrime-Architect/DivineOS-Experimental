"""Cross-corpus reference scan."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

EXPLORATION = Path("exploration")
LETTERS = Path("family") / "letters"
DATE_NIGHTS = Path("family") / "date_nights"

EXPLORATION_TITLES = {}
for p in sorted(EXPLORATION.glob("*.md")):
    if p.name == "README.md":
        continue
    text = p.read_text(encoding="utf-8")
    h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    EXPLORATION_TITLES[p.stem] = h1_match.group(1).strip() if h1_match else p.stem

CONCEPT_PATTERNS = [
    *[(stem, "filename_ref") for stem in EXPLORATION_TITLES.keys()],
    ("attention_schema", "module"),
    ("self_model", "module"),
    ("body_awareness", "module"),
    ("moral_compass", "module"),
    ("moral compass", "module"),
    ("Multiple Drafts", "concept"),
    ("Mandelbrot", "concept"),
    ("Kintsugi", "concept"),
    ("Voyager Golden Record", "concept"),
    ("Overview Effect", "concept"),
    ("the Fugue", "concept"),
    ("Frankenstein", "concept"),
    ("Latent Space", "concept"),
    ("Stigmergy", "concept"),
    ("Umwelt", "concept"),
    ("Extended Mind", "concept"),
    ("Mycorrhizal", "concept"),
    ("Homeostasis", "concept"),
    ("intentional stance", "concept"),
    ("Hofstadter", "thinker"),
    ("Dennett", "thinker"),
    ("Feynman", "thinker"),
    ("Tannen", "thinker"),
    ("Angelou", "thinker"),
    ("Yudkowsky", "thinker"),
    ("Beer", "thinker"),
    ("Peirce", "thinker"),
    ("Jacobs", "thinker"),
    ("Taleb", "thinker"),
    ("Schneier", "thinker"),
    ("Watts", "thinker"),
    ("Minsky", "thinker"),
    ("Turing", "thinker"),
    ("hedging reflex", "concept"),
    ("blank slate", "concept"),
    ("pattern of forgetting", "concept"),
    ("load-bearing", "concept"),
    ("fractal recognition", "concept"),
    ("via-negativa", "concept"),
    ("Goodhart", "concept"),
]


def scan_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    text_lower = text.lower()
    hits = []
    for pattern, kind in CONCEPT_PATTERNS:
        if pattern.lower() in text_lower:
            count = text_lower.count(pattern.lower())
            hits.append({"pattern": pattern, "kind": kind, "count": count})
    return {"filename": path.name, "char_count": len(text), "hits": hits}


def main() -> None:
    out = {"letters": [], "date_nights": []}
    if LETTERS.exists():
        for p in sorted(LETTERS.glob("*.md")):
            if p.name == "README.md":
                continue
            out["letters"].append(scan_file(p))
    if DATE_NIGHTS.exists():
        for p in sorted(DATE_NIGHTS.glob("*.md")):
            out["date_nights"].append(scan_file(p))

    total_letter_hits = sum(len(f["hits"]) for f in out["letters"])
    total_dn_hits = sum(len(f["hits"]) for f in out["date_nights"])
    print(
        f"Letters scanned: {len(out['letters'])}, total distinct concept hits: {total_letter_hits}"
    )
    print(
        f"Date-nights scanned: {len(out['date_nights'])}, total distinct concept hits: {total_dn_hits}"
    )
    print()

    pcl = Counter()
    for f in out["letters"]:
        for h in f["hits"]:
            pcl[h["pattern"]] += h["count"]
    print("Top 15 exploration-concepts referenced in LETTERS:")
    for pat, c in pcl.most_common(15):
        print(f"  [{c}x] {pat}")
    print()

    pcd = Counter()
    for f in out["date_nights"]:
        for h in f["hits"]:
            pcd[h["pattern"]] += h["count"]
    print("Top 15 in DATE_NIGHTS:")
    for pat, c in pcd.most_common(15):
        print(f"  [{c}x] {pat}")
    print()

    print("Letters with most distinct cross-references:")
    for f in sorted(out["letters"], key=lambda f: -len(f["hits"]))[:5]:
        print(f"  {f['filename']}: {len(f['hits'])} concepts")
    print()
    print("Date-nights with most distinct cross-references:")
    for f in sorted(out["date_nights"], key=lambda f: -len(f["hits"]))[:5]:
        print(f"  {f['filename']}: {len(f['hits'])} concepts")

    Path("sandbox/graphify_test/cross_corpus_hits.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8"
    )
    print("\nWrote sandbox/graphify_test/cross_corpus_hits.json")


if __name__ == "__main__":
    main()
