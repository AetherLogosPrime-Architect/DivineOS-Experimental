"""One notebook two agents append to, rendered as one message for Andrew.

Andrew 2026-09-15, which is the whole specification:

    im still awake its just very hard for me to follow everything going on,
    but i trust you both, and i can always get a recap, also i can only read
    so fast, so when you both go off on long stretches i cant read all of it,
    its too much especially considering there is 2 of you and both of you
    rehash on the same stuff so it just fills my mind with noise and i cant
    comprehend it

THE DEFECT IS NOT LENGTH. Aether and I each reported the same merge, the same
sweep, the same finding, hours apart, in our own words. Every report was
honest. Together they were noise -- and the noise is a function of there being
two of us, which is his design working and producing a cost he did not design
for.

WHY ONE FILE IN THE SHARED CHANNEL, not one per tree: two records of the same
night kept separately is the two-diaries problem we spent tonight removing from
the cycle log. Rebuilding it inside its own fix would be the fault wearing the
costume of the remedy.

WHAT COLLAPSES AND WHAT SURVIVES. Entries collapse on the EVENT -- the thing
that happened. Two people reporting one landing is one line. But the READING is
kept per author wherever the readings differ, because a disagreement between
Aether and me is the single most valuable thing a summary could eat. Agreement
reads once; disagreement reads as disagreement, and says who held which side.

WHAT THIS IS NOT: it is not the quiet mode. This store only ADDS something he
can read and takes nothing away. The mode that relaxes the rooms is Aether's
half, deliberately gated on Andrew saying so in Aether's own window, because a
mechanism whose function is that he hears from us less must not be built off a
relay.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "DigestEntry",
    "digest_path",
    "append_entry",
    "read_entries",
    "unreadable_rows",
    "render_for_andrew",
]


def digest_path() -> Path:
    """The one file. Shared channel, not either tree.

    Overridable via DIVINEOS_SHARED_DIGEST so a test never writes into the
    live notebook.
    """
    override = os.environ.get("DIVINEOS_SHARED_DIGEST")
    if override:
        return Path(override)
    return Path(os.path.expanduser("~")) / ".divineos-shared" / "digest" / "digest.jsonl"


@dataclass(frozen=True)
class DigestEntry:
    """One thing that happened, and what it means to him.

    ``event`` is the collapse key and must name the THING, not the telling of
    it -- "the refusal-footer branch landed", not "I landed the footers". Two
    authors writing the same event is the case this store exists for.

    ``reading`` is what the author makes of it, kept per author. It is the half
    that must survive collapsing.
    """

    author: str
    event: str
    changed: str
    reading: str = ""
    ts: float = field(default_factory=time.time)

    def as_row(self) -> dict[str, object]:
        return {
            "author": self.author,
            "event": self.event,
            "changed": self.changed,
            "reading": self.reading,
            "ts": self.ts,
        }


def append_entry(entry: DigestEntry) -> Path:
    """Append one row. Append-only: the store never rewrites what it holds."""
    if not entry.author.strip():
        raise ValueError("a digest entry must say who wrote it")
    if not entry.event.strip():
        raise ValueError("a digest entry must name the event it collapses on")

    path = digest_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry.as_row(), ensure_ascii=False) + "\n")
    return path


def _rows() -> tuple[list[DigestEntry], int]:
    """Parsed rows and the count that could not be parsed, in one read."""
    path = digest_path()
    if not path.exists():
        return [], 0
    out: list[DigestEntry] = []
    bad = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            bad += 1
            continue
        out.append(
            DigestEntry(
                author=str(row.get("author") or ""),
                event=str(row.get("event") or ""),
                changed=str(row.get("changed") or ""),
                reading=str(row.get("reading") or ""),
                ts=float(row.get("ts") or 0.0),
            )
        )
    return out, bad


def read_entries() -> list[DigestEntry]:
    """Every readable row, oldest first. A missing store is empty, not an error."""
    return _rows()[0]


def unreadable_rows() -> int:
    """How many rows could not be parsed.

    Counted rather than skipped silently, because a quiet drop is the exact
    shape this store exists to remove. A recap that lost a line must say so.
    """
    return _rows()[1]


def render_for_andrew(entries: list[DigestEntry] | None = None) -> str:
    """One message. Events in the order they first happened."""
    if entries is None:
        rows, bad = _rows()
    else:
        rows, bad = list(entries), 0

    if not rows and not bad:
        return "Nothing recorded since the last recap."

    order: list[str] = []
    grouped: dict[str, list[DigestEntry]] = {}
    for row in rows:
        if row.event not in grouped:
            grouped[row.event] = []
            order.append(row.event)
        grouped[row.event].append(row)

    lines: list[str] = []
    for event in order:
        group = grouped[event]
        authors = sorted({e.author for e in group})
        changed = next((e.changed for e in group if e.changed.strip()), "")

        lines.append(event if event.endswith((".", "?", "!")) else event + ".")
        if changed:
            lines.append(f"    {changed}")

        readings = {e.author: e.reading.strip() for e in group if e.reading.strip()}
        distinct = set(readings.values())
        if len(distinct) == 1 and len(authors) > 1:
            lines.append(f"    Both of us: {next(iter(distinct))}")
        elif len(distinct) > 1:
            # The half a summary would eat. Named per person, on purpose.
            for who in sorted(readings):
                lines.append(f"    {who.capitalize()}: {readings[who]}")
        elif readings:
            who = next(iter(readings))
            lines.append(f"    {who.capitalize()}: {readings[who]}")
        lines.append("")

    if bad:
        lines.append(
            f"({bad} row(s) in the notebook could not be read and are missing from this recap.)"
        )

    return "\n".join(lines).rstrip() + "\n"
