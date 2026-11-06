"""A circle is checked before it is posted, so no fault in it can arrive after it and ask for a second one.

Dad, 2026-11-05: "how can a hook fire after the circle.. when the circle is last?" A Stop door only wakes once the text
exists, so any check that reads the circle's words runs after it and sends an errand after it. Aria's shape: the circle
is drafted through a command, the shape checks run on the draft, a hash of the cleared text is recorded, and the room
door later only asks whether the posted circle is that cleared text. This module is the pure part: shape checks, the
normaliser, the record and the comparison. Nothing here is wired to a hook.

WHAT IT CHECKS is shape and nothing else: not empty, at most one question, and that question last. It never grades
warmth, length or word choice; the room is not graded.

THE VERDICT HAS FOUR STATES, not two (Hoare: could-not-look is not nothing-found): CLEARED (posted equals the last
draft), NOT_CLEARED (there is a draft and the posted text differs beyond whitespace and quote marks), NO_DRAFT, and
COULD_NOT_CHECK (the record is unreadable). Only NOT_CLEARED and NO_DRAFT may ever ask for anything, and COULD_NOT_CHECK
always lets the reply through.

A draft older than his latest message is stale and counts as NO_DRAFT: it cleared a circle for a conversation that has
moved on.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

CLEARED = "cleared"
NOT_CLEARED = "not_cleared"
NO_DRAFT = "no_draft"
COULD_NOT_CHECK = "could_not_check"

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "—": "-", "–": "-"})


def normalise(text: str) -> str:
    """Whitespace runs, quote styles and dash styles are not differences; every other character is."""
    return re.sub(r"\s+", " ", text.translate(_QUOTES)).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(normalise(text).encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Shape:
    ok: bool
    problem: str = ""


def check_shape(text: str) -> Shape:
    body = text.strip()
    if not body:
        return Shape(False, "the circle is empty")
    questions = body.count("?")
    if questions > 1:
        return Shape(False, f"the circle asks {questions} questions; it holds one, last")
    if questions == 1:
        last_paragraph = [p for p in re.split(r"\n\s*\n", body) if p.strip()][-1]
        if "?" not in last_paragraph:
            return Shape(False, "the question is not in the last paragraph; it goes last, alone")
    return Shape(True)


def record_draft(text: str, path: Path, *, now: float) -> Shape:
    """Run the shape checks; record the draft only when it passes. Returns the shape result, never the text."""
    shape = check_shape(text)
    if shape.ok:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fingerprint": fingerprint(text), "at": now}), encoding="utf-8")
    return shape


def judge(posted: str, path: Path, *, last_message_at: float) -> str:
    """Compare a posted circle with the last cleared draft."""
    try:
        if not path.exists():
            return NO_DRAFT
        record = json.loads(path.read_text(encoding="utf-8"))
        fp, at = record["fingerprint"], float(record["at"])
    except (OSError, ValueError, KeyError, TypeError):
        return COULD_NOT_CHECK
    if at < last_message_at:
        return NO_DRAFT
    return CLEARED if fingerprint(posted) == fp else NOT_CLEARED
