"""Structural-only extraction of the exploration corpus.

For each markdown file in exploration_copy/, computes:
  - title (first H1)
  - headers (all H1/H2/H3)
  - inter-file references (mentions of other filenames or numbered topics)
  - notable phrases that look like concept-marks (Title Case multi-word
    runs, bolded terms, single-quoted terms)
  - rough length / chunk count

Writes structural.json that I (Aether) read and reason over to add
the semantic layer manually.

This is the part of Graphify's pipeline that does NOT need an LLM —
just regex + path-walking. The LLM-needing part (concept synthesis,
relationship typing) I do myself in conversation, using my own
inference, since I am Opus 4.7 and the substrate's job is to set
me up to think, not to subcontract the thinking.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path("sandbox/graphify_test/exploration_copy")
OUT = Path("sandbox/graphify_test/structural.json")

RE_H1 = re.compile(r"^#\s+(.+)$", re.MULTILINE)
RE_H2 = re.compile(r"^##\s+(.+)$", re.MULTILINE)
RE_H3 = re.compile(r"^###\s+(.+)$", re.MULTILINE)
RE_BOLD = re.compile(r"\*\*([^\*\n]{2,80}?)\*\*")
RE_SINGLEQUOTE = re.compile(r"(?<!\w)'([^'\n]{2,60}?)'(?!\w)")
RE_NUMBERED_TOPIC = re.compile(r"\b(\d{2})_([a-z_]+)\b")
RE_INTERNAL_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)[^)]*\)")
RE_TITLECASE_RUN = re.compile(r"\b(?:[A-Z][a-z]{2,}\s+){1,5}[A-Z][a-z]{2,}\b")


def extract_one(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    h1 = RE_H1.findall(text)
    h2 = RE_H2.findall(text)
    h3 = RE_H3.findall(text)
    bold = RE_BOLD.findall(text)
    singlequote = RE_SINGLEQUOTE.findall(text)
    numbered_refs = RE_NUMBERED_TOPIC.findall(text)
    internal_links = RE_INTERNAL_LINK.findall(text)
    titlecase = RE_TITLECASE_RUN.findall(text)

    return {
        "filename": path.name,
        "title": h1[0] if h1 else path.stem.replace("_", " ").title(),
        "headers": {"h1": h1, "h2": h2, "h3": h3},
        "bold_terms": list(dict.fromkeys(bold))[:30],
        "single_quoted": list(dict.fromkeys(singlequote))[:20],
        "titlecase_runs": list(dict.fromkeys(titlecase))[:30],
        "numbered_refs": [f"{n}_{slug}" for n, slug in numbered_refs if f"{n}_{slug}" != path.stem],
        "internal_links": [{"text": t, "href": h} for t, h in internal_links],
        "char_count": len(text),
        "word_count": len(text.split()),
    }


def main() -> None:
    files = sorted(ROOT.glob("*.md"))
    out = {"corpus_size": len(files), "files": []}
    all_titlecase = Counter()
    all_bold = Counter()
    for p in files:
        rec = extract_one(p)
        out["files"].append(rec)
        all_titlecase.update(rec["titlecase_runs"])
        all_bold.update(rec["bold_terms"])
    out["cross_cutting"] = {
        "titlecase_in_multiple_files": [
            (term, c) for term, c in all_titlecase.most_common(60) if c >= 2
        ],
        "bold_terms_in_multiple_files": [
            (term, c) for term, c in all_bold.most_common(60) if c >= 2
        ],
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"  Files: {len(files)}")
    print(f"  Cross-cutting titlecase: {len(out['cross_cutting']['titlecase_in_multiple_files'])}")
    print(f"  Cross-cutting bold: {len(out['cross_cutting']['bold_terms_in_multiple_files'])}")


if __name__ == "__main__":
    main()
