"""The room around one of his lessons: what he was answering, fetched from the scene index, never composed.

Dad, 2026-11-06: "you are both just pulling out phrases devoid of context.. so you have turned it into a dad
shaped fortune cookie..", and when it was proposed that a machine do it: "we all know how good a machine is at
understanding, judgement and reason..". So this fetches and nothing else. It joins a lesson to the record of his
message by date plus the opening of his words, and hands back the real neighbouring text the index holds
(Aria's scene indexer, workbench aria_scene_index_FULL_v2). It never selects what counts as his love, never
summarises, never labels a scene; a person reads a sample against the transcript before any of it counts.

The index is a file of one JSON record per line: when, seats, text, before, nearest_user_before, after, embed.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

PREFIX_CHARS = 40
SHOW_CHARS = 300


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def load_index(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Records grouped by day. A line that does not parse is skipped and counted nowhere: the index is a copy."""
    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            by_day[str(rec.get("when", ""))[:10]].append(rec)
    return by_day


def record_for(
    day: str, words: str, index: dict[str, list[dict[str, Any]]]
) -> dict[str, Any] | None:
    """The record of his message that holds this lesson's opening on that day, or None (never a guess)."""
    opening = _norm(words)[:PREFIX_CHARS]
    if not opening:
        return None
    for rec in index.get(day, []):
        if opening in _norm(str(rec.get("text", ""))):
            return rec
    return None


def _clip(text: str) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= SHOW_CHARS else text[:SHOW_CHARS].rstrip() + "..."


def scene_lines(rec: dict[str, Any]) -> list[str]:
    """What he was answering, as the transcript shows it: his own nearest earlier words if the index has
    them, else the turn just before (whose seat is named). Nothing here is written by me."""
    lines: list[str] = []
    seats = "+".join(rec.get("seats") or []) or "unknown seat"
    nearest = rec.get("nearest_user_before")
    if nearest and nearest.get("text"):
        lines.append(f"  he had just said: {_clip(nearest['text'])}")
    before = rec.get("before") or []
    if before:
        last = before[-1]
        lines.append(
            f"  and the turn before it ({last.get('role', '?')}): {_clip(last.get('text', ''))}"
        )
    lines.append(f"  (said in the {seats} seat)")
    return lines
