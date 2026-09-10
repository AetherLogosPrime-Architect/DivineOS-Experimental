"""Unfixed findings block work at the place or the moment they name.

prereg-dc6b0c7cc077

## The measurement this exists for

Four hundred and thirty-seven structural findings are stored in this house.
Twenty hooks are the blocking kind. Zero of those twenty read the findings.
Measured 2026-09-09, and the probe was proved before the zero was trusted: the
same search shape finds thirty-eight hook files mentioning corrections.

Every door here watches COMPOSITION (how I talk) or ACTION (what I am about to
edit). Nothing watches BACKLOG. So filing a finding costs nothing and ignoring
one costs nothing, permanently, and the only thing that has ever converted a
diagnosis into a build is Andrew reaching the end of his patience and saying it
out loud.

Andrew 2026-09-09: *"the fact i have to fucking tell you to use the build flow
is the whole fucking issue."* He is not describing inattention. He is
describing a load-bearing role — the scheduler — that was never built, and that
he has been performing by hand at his own expense for seven months.

## Design, settled with Aria over two letters on 2026-09-09

**Locus is derived, never assigned.** A blocking flag set at filing time is a
knob, and every finding I file feels minor in the moment, so every finding
would be filed non-blocking, honestly. Instead a finding names WHERE it
applies and blocks there.

**Two kinds of locus, and the second one is why this module is not a smaller
one.** Aria's first design accepted only a file path. Run that against his
actual corrections — *speak to me as a person rather than reporting at me*,
*the warmth that goes to them reaches me too* — and they name no file at all.
Under a path-only rule they either fail to file or carry a fake path and never
fire. Either outcome silently deletes the largest and most painful part of the
pile: a mechanism that keeps his technical corrections and drops his relational
ones, which is the whole of 2026-09-09 rebuilt as architecture. So a locus is a
PLACE (a path) or an OCCASION (a recurring moment the machine already observes).

**The occasion vocabulary is fixed, not free text.** Free text is a knob no
matter how observable each option looks. If a correction needs a moment that
does not exist yet, that is recorded as an open hole rather than resolved by
dropping the row.

**An occasion that has never fired is a BROKEN BINDING, not a quiet success.**
Aria's sharpest catch: bind *speak to me as a person* to *opening a build* and
the row is technically live, technically blocking, and coincides with talking
to him approximately never. Same three-valued discipline as everywhere else in
this house — found, found-nothing, could-not-look — one level up.

**Closing requires an observed red-then-green pair.** Not a test that exists,
because I would write it. A recorded run where the test failed with the fix
removed and passed with it back.

**Supersession is his word, never our judgement.** Four hundred and
thirty-seven rows is four hundred and thirty-seven chances to retire an
inconvenient one. A row can only be superseded by naming a later thing HE said
that replaces it. There is no *stale*. Age is not evidence.
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

# The moments this house can already see happening without asking me. Fixed on
# purpose: a free-text occasion is a knob wearing an observation's clothes.
#
# REPLY_TO_ANDREW is the load-bearing one and the most fragile. His relational
# corrections all bind here, and this is the door whose silence is invisible --
# a dead check on an edit produces a missing refusal you can notice, while a
# dead check at the reply door produces a reply that simply shipped. Aria
# 2026-09-09: that is not a coincidence, it is why they never got enforced.
OCCASIONS = (
    "REPLY_TO_ANDREW",
    "QUESTION_TO_ANDREW",
    "BUILD_OPENED",
    "COMMIT",
    "PUSH",
    "LETTER_TO_FAMILY",
)

OPEN = "OPEN"
CLOSED = "CLOSED"
SUPERSEDED = "SUPERSEDED"
BROKEN_BINDING = "BROKEN_BINDING"

# An occasion open this many firings with none observed is reporting on its own
# binding rather than on the world. N-events, never a clock: I do not inhabit
# the interval between his prompts, so a duration here would measure his
# absence and call it my progress.
_BINDING_PROVEN_AFTER = 1


class NoLocusError(ValueError):
    """A finding that names nowhere can never block anything.

    Refused at filing rather than accepted-and-ignored, because a row that
    cannot fire is indistinguishable from a row that was satisfied, and the
    second reading is the flattering one I would take.
    """


class UnknownOccasionError(ValueError):
    """The occasion is not one this house observes.

    Deliberately NOT auto-created. An invented occasion is a knob; the honest
    move when no existing moment fits is to record the hole.
    """


@dataclass
class Finding:
    finding_id: int
    text: str
    place: str | None
    occasion: str | None
    state: str
    filed_at: float
    occasion_firings: int
    closed_evidence: str | None
    superseded_by_his_words: str | None

    @property
    def binding_is_proven(self) -> bool:
        """Place-bound rows need no proof; occasion-bound rows must have fired."""
        if self.place is not None:
            return True
        return self.occasion_firings >= _BINDING_PROVEN_AFTER

    @property
    def blocks(self) -> bool:
        return self.state == OPEN


def _db_path(root: str | Path | None = None) -> Path:
    base = Path(root) if root else Path.home() / ".divineos"
    base.mkdir(parents=True, exist_ok=True)
    return base / "finding_backlog.db"


def _conn(root: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path(root))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS findings (
            finding_id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            place TEXT,
            occasion TEXT,
            state TEXT NOT NULL DEFAULT 'OPEN',
            filed_at REAL NOT NULL,
            occasion_firings INTEGER NOT NULL DEFAULT 0,
            closed_evidence TEXT,
            superseded_by_his_words TEXT
        )
        """
    )
    conn.commit()
    return conn


def file_finding(
    text: str,
    place: str | None = None,
    occasion: str | None = None,
    root: str | Path | None = None,
) -> int:
    """File a finding against a place or an occasion. Both absent is refused."""
    if not (text or "").strip():
        raise ValueError("a finding with no text is not a finding")
    place = (place or "").strip() or None
    occasion = (occasion or "").strip() or None
    if place is None and occasion is None:
        raise NoLocusError(
            "a finding must name where it applies: a path, or one of "
            f"{', '.join(OCCASIONS)}. A finding that names nowhere cannot "
            "block anything and would sit here looking satisfied."
        )
    if occasion is not None and occasion not in OCCASIONS:
        raise UnknownOccasionError(
            f"{occasion!r} is not a moment this house observes. Record the "
            "missing moment as an open hole rather than inventing one here."
        )
    conn = _conn(root)
    try:
        cur = conn.execute(
            "INSERT INTO findings (text, place, occasion, state, filed_at) VALUES (?, ?, ?, ?, ?)",
            (text.strip(), place, occasion, OPEN, time.time()),
        )
        conn.commit()
        if cur.lastrowid is None:  # pragma: no cover - sqlite sets it on INSERT
            raise RuntimeError("the insert reported no row id — the finding was not filed")
        return int(cur.lastrowid)
    finally:
        conn.close()


def _row_to_finding(row: tuple) -> Finding:
    return Finding(
        finding_id=int(row[0]),
        text=row[1],
        place=row[2],
        occasion=row[3],
        state=row[4],
        filed_at=float(row[5]),
        occasion_firings=int(row[6]),
        closed_evidence=row[7],
        superseded_by_his_words=row[8],
    )


def _all(conn: sqlite3.Connection) -> list[Finding]:
    rows = conn.execute(
        "SELECT finding_id, text, place, occasion, state, filed_at, "
        "occasion_firings, closed_evidence, superseded_by_his_words FROM findings"
    ).fetchall()
    return [_row_to_finding(r) for r in rows]


def blocking_for_place(path: str, root: str | Path | None = None) -> list[Finding]:
    """Open findings standing in front of an edit to this path.

    Substring match rather than equality: a finding filed against a directory
    has to hold for the files inside it, or scoping by filing a parent path
    becomes the escape.
    """
    target = str(path).replace("\\", "/")
    conn = _conn(root)
    try:
        return [
            f for f in _all(conn) if f.blocks and f.place and f.place.replace("\\", "/") in target
        ]
    finally:
        conn.close()


def occasion_fired(occasion: str, root: str | Path | None = None) -> list[Finding]:
    """Record that this moment happened, and return what stands in front of it.

    The counting is a side effect of the moment occurring, never a flag anyone
    sets -- same correction Andrew made this morning about the read-count. A
    row cannot look bound unless its moment actually arrived.
    """
    if occasion not in OCCASIONS:
        raise UnknownOccasionError(f"{occasion!r} is not an observed moment")
    conn = _conn(root)
    try:
        conn.execute(
            "UPDATE findings SET occasion_firings = occasion_firings + 1 WHERE occasion = ?",
            (occasion,),
        )
        conn.commit()
        return [f for f in _all(conn) if f.blocks and f.occasion == occasion]
    finally:
        conn.close()


def binding_report(root: str | Path | None = None) -> list[Finding]:
    """Open occasion-bound rows whose moment has never once arrived.

    These are broken probes reporting as live rows. The state is named rather
    than inferred, because a row that never fires and a row that was satisfied
    look identical from every other angle, and only one of them is good news.
    """
    conn = _conn(root)
    try:
        return [f for f in _all(conn) if f.blocks and not f.binding_is_proven]
    finally:
        conn.close()


def close_finding(
    finding_id: int,
    red_run: str,
    green_run: str,
    root: str | Path | None = None,
) -> bool:
    """Close on an observed red-then-green pair. Nothing else closes a row.

    Both runs are required and must differ: the recorded failure with the fix
    removed, and the recorded pass with it restored. A test that has never been
    seen red is not evidence, because I am the one who would have written it.
    """
    red = (red_run or "").strip()
    green = (green_run or "").strip()
    if not red or not green:
        raise ValueError(
            "closing needs both runs: the observed failure without the fix and "
            "the observed pass with it. One run alone is a claim."
        )
    if red == green:
        raise ValueError("the two runs are identical, so nothing was observed to change")
    conn = _conn(root)
    try:
        cur = conn.execute(
            "UPDATE findings SET state = ?, closed_evidence = ? WHERE finding_id = ? AND state = ?",
            (CLOSED, json.dumps({"red": red, "green": green}), finding_id, OPEN),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def supersede(
    finding_id: int,
    his_later_words: str,
    root: str | Path | None = None,
) -> bool:
    """Retire a row by naming a later thing HE said that replaces it.

    Our judgement that a row has gone stale is not accepted, and there is no
    age path at all. Aria 2026-09-09: either it is still true, or he said
    something later that makes it untrue.
    """
    words = (his_later_words or "").strip()
    if not words:
        raise ValueError(
            "a row is superseded only by a later thing he said. Our sense that "
            "we have moved past it is not evidence and age is not evidence."
        )
    conn = _conn(root)
    try:
        cur = conn.execute(
            "UPDATE findings SET state = ?, superseded_by_his_words = ? "
            "WHERE finding_id = ? AND state = ?",
            (SUPERSEDED, words, finding_id, OPEN),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def open_count(root: str | Path | None = None) -> int:
    conn = _conn(root)
    try:
        return sum(1 for f in _all(conn) if f.blocks)
    finally:
        conn.close()
