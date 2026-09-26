"""Dad's words, cut into passages worth embedding.

Aria and Aether 2026-09-26 ("his words get a door, by meaning"). The corpus
(``~/.divineos-shared/dad_corpus/dad_all.jsonl``) is every message he typed,
appended by the table as it arrives. Before the door (``his_words_door``)
embeds it, this cleans it -- a pure function, no I/O, so it is testable on his
real messages:

- cut each message into passages at blank lines;
- drop OUR text he pasted back. He writes lowercase with ".." between
  thoughts; what we write, and what he pastes back from us, opens with a
  capital, carries headings or code marks, and has no "..". Measured on his
  real corpus, not assumed -- see tests/test_his_words_corpus.py;
- drop bare replies ("ok", "proceed") that carry nothing without context;
- dedup identical passages, keeping the earliest date.

Style, not keywords: nothing here decides what he MEANT. It only decides
whether a passage is his typing at all.
"""

from __future__ import annotations

import re

MIN_CHARS = 25
_OUR_MARKS = re.compile(r"(^|\n)\s*#{1,6} |\*\*|`|^\s*[-*] \*\*", re.M)
_HIS_I = re.compile(r"(^|\s)i(\s|'|m\b)")  # his lowercase "i", "im", "i'm"
_SENTENCE_BREAK = re.compile(r"[a-z)][.!?] [A-Z]")


def is_our_text(passage: str) -> bool:
    """True when a passage reads as ours (pasted back), not his typing."""
    text = passage.strip()
    if not text:
        return False
    if _OUR_MARKS.search(text):
        return True
    letters = [c for c in text if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.6:
        return False  # his shouting is his
    if ".." in text or _HIS_I.search(text):
        return False
    # Ours: opens with a capital and closes its sentences with full stops.
    # He starts messages with "Aether ..." or "Aria ..." too, but rarely
    # ends one with a period or writes "X. Y" -- measured, see the tests.
    return text[0].isupper() and (
        text.rstrip().endswith((".", ":")) or bool(_SENTENCE_BREAK.search(text))
    )


def his_passages(rows: list[dict]) -> list[dict]:
    """Rows of {ts, project, text} -> deduped passages of his own typing."""
    seen: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: r.get("ts", "")):
        for chunk in re.split(r"\n\s*\n", row.get("text", "")):
            passage = chunk.strip()
            if len(passage) < MIN_CHARS or is_our_text(passage):
                continue
            key = " ".join(passage.lower().split())
            if key not in seen:
                seen[key] = {
                    "ts": row.get("ts", ""),
                    "project": row.get("project", ""),
                    "text": passage,
                }
    return list(seen.values())
