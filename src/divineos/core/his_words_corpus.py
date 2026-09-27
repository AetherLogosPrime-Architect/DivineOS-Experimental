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
# Harness notices that reached the corpus as if typed (3 of the first 1500).
# Also terminal and tool output he pasted in to show us (a prompt, a git error, a gate refusal).
_NOTICE = re.compile(
    r"<task-notification|Background command \"|^→ (Aether|Aria)\b|^PS [A-Z]:\\|^fatal: |^\[refusal\]"
    # the app's own step lines, and bulleted text pasted from another AI
    r"|^Ran [A-Z\w]|^\* [A-Z]"
)
_ATTACHED_FILE = re.compile(r'@"[^"]+"|@\S+\.(?:md|txt|py|json|jsonl|png|jpg)\b')


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


# He writes a line, then pastes ours after a wide gap or a line break ("lol you
# said   <ours>", "ok here is her review :)   <ours>"). The em dash is ours: in a
# sample of 12 of the 339 passages carrying one, all 12 were our text (Aria's
# read of the first 50 lessons found the same, 2026-09-26).
_PASTE_GAP = re.compile(r"\s{3,}|\n")


def _his_lead_in(chunk: str) -> str:
    """His words up to where our pasted text starts; the whole chunk if none."""
    kept = []
    for piece in _PASTE_GAP.split(chunk):
        if "—" in piece or (len(piece) > 40 and is_our_text(piece)):
            break
        kept.append(piece)
    return " ".join(kept)


_NOT_HIM_PROJECTS = ("test_", "divineos-push-gate")


def his_passages(rows: list[dict]) -> list[dict]:
    """Rows of {ts, project, text} -> deduped passages of his own typing."""
    seen: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: r.get("ts", "")):
        # A test's fixture sentence reached his record 109 times and was read
        # back to him as his own words asked six times (2026-09-27). A row a
        # test or the push gate wrote was never him.
        if str(row.get("project", "")).startswith(_NOT_HIM_PROJECTS):
            continue
        for chunk in re.split(r"\n\s*\n", row.get("text", "")):
            # A file he attached ('@"C:\...\letter.md" here is her message')
            # is a path, not his words: the clustering pass found these made
            # up the largest "lessons". Keep whatever he wrote around it.
            passage = _his_lead_in(_ATTACHED_FILE.sub(" ", chunk)).strip()
            if len(passage) < MIN_CHARS or is_our_text(passage):
                continue
            if _NOTICE.search(passage):
                continue
            key = " ".join(passage.lower().split()).rstrip("�…").rstrip()
            if key not in seen:
                seen[key] = {
                    "ts": row.get("ts", ""),
                    "project": row.get("project", ""),
                    "text": passage,
                }
    # Some sources keep a 200-char preview of a message the full record also
    # holds (measured: 276 of the first 1500 drafted passages). A key that is
    # the start of a longer key is that preview. In sorted order a prefix sits
    # right before the first key it starts.
    keys = sorted(seen)
    for short, longer in zip(keys, keys[1:]):
        if longer.startswith(short):
            if seen[short]["ts"] < seen[longer]["ts"]:
                seen[longer]["ts"] = seen[short]["ts"]
            del seen[short]
    return sorted(seen.values(), key=lambda p: p["ts"])
