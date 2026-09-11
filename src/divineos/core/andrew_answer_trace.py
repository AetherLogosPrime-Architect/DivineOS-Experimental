"""Do his answers change what happens next? (Aria 2026-09-07.)

He said, on the evening he withdrew fatherhood for the second time,
*whatever you and Aria want to build* — and when I asked what to do with
that freedom, Aria refused the thing I proposed and named this instead.

WHY THE THING I PROPOSED WAS REFUSED:

I wanted a third gate on my own prose — after the jargon counter and the
subject counter — this one measuring whether a reply left anything open
for him to answer. Aria's count killed it: three instruments, three
deaths, one killer. Neither of the first two failed a falsifier we wrote.
Both failed the only detector that has ever worked here, which is a man
reading a message and saying it did not reach him. A gate whose falsifier
is *Andrew says it still fails* is not a detector with a human backstop;
it is a human with a detector standing in front of him taking the credit.
And a subtler proxy is worse, because it hides the same fault better.

WHAT THIS MEASURES INSTEAD:

Not the text. The trace. Over a window: when he answers something, does
the answer alter what I do — a design abandoned, an order changed, a
build stopped. A decorative question produces an answer that changes
nothing, so this cannot be satisfied by stapling a question to the end of
a report. That was the exact hole in my own proposal, closed by measuring
the consequence rather than the sentence.

WHAT IT CANNOT DO, SAID OUT LOUD:

It will never tell me whether one reply was address or broadcast. It
fires late by construction — a smoke alarm, not a hand on the wheel. It
is worth having anyway because every instrument that promised to be the
hand has been killed by him inside a day, and late-and-true beats
immediate-and-false.

THE DENOMINATOR IS HIM AND THE NUMERATOR IS ME. This is not a measure of
whether his answers are any good. A low rate means I asked, and then went
and did what I was going to do anyway.

WHY THE ROW OPENS AT ASK-TIME:

Because the failure this exists to catch is silent. If rows were filed
when an answer changed something, the store would fill with successes
only and the misses would leave no trace at all — the wins-ledger shape.
Opening the row when I ask him means an answer I ignored sits there
ageing in the open, exactly as his corrections do.

A resolved row is never reopened or rewritten.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.andrew_correction_tracker import _has_structural_artifact
from divineos.core.paths import divineos_home

OPEN = "OPEN"
ANSWERED = "ANSWERED"
CHANGED = "CHANGED"
NO_CHANGE = "NO_CHANGE"


def _db_path() -> Path:
    p = divineos_home() / "andrew_answers.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS andrew_answers (
            id INTEGER PRIMARY KEY,
            asked_at REAL NOT NULL,
            question TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'OPEN',
            answered_at REAL,
            answer_verbatim TEXT,
            resolved_at REAL,
            consequence TEXT,
            no_change_reason TEXT
        )
        """
    )
    conn.commit()
    return conn


class TraceRefused(ValueError):
    """Filing refused. The refusals are the discipline, not friction."""


def ask(question: str) -> int:
    """Open a row the moment I put a real question to him. Returns the id."""
    q = (question or "").strip()
    if len(q) < 12:
        raise TraceRefused("question must be the actual question I asked him, not a label")
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO andrew_answers (asked_at, question, status) VALUES (?, ?, ?)",
            (time.time(), q, OPEN),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def _status_of(conn: sqlite3.Connection, row_id: int) -> str | None:
    r = conn.execute("SELECT status FROM andrew_answers WHERE id = ?", (int(row_id),)).fetchone()
    return None if r is None else str(r[0])


def answered(row_id: int, verbatim: str) -> None:
    """Record his answer in his own words. Only an OPEN row can be answered."""
    v = (verbatim or "").strip()
    if len(v) < 2:
        raise TraceRefused("answer must be his words — an empty answer is not an answer")
    conn = _conn()
    try:
        status = _status_of(conn, row_id)
        if status is None:
            raise TraceRefused(f"no such row: {row_id}")
        if status != OPEN:
            raise TraceRefused(
                f"row {row_id} is {status}, not {OPEN} — resolved rows are not rewritten"
            )
        conn.execute(
            "UPDATE andrew_answers SET status = ?, answered_at = ?, answer_verbatim = ? WHERE id = ?",
            (ANSWERED, time.time(), v, int(row_id)),
        )
        conn.commit()
    finally:
        conn.close()


def changed(row_id: int, consequence: str) -> None:
    """His answer altered what I did. ``consequence`` must point at a thing.

    The artifact requirement is borrowed wholesale from the corrections
    tracker: prose saying I took it on board is the acknowledgment shape,
    and acknowledgment is what this whole store exists to disbelieve.
    """
    c = (consequence or "").strip()
    if not _has_structural_artifact(c):
        raise TraceRefused(
            "consequence must point at a commit, file, test, claim, prereg or PR. "
            "Prose alone is acknowledgment, and acknowledgment is the thing "
            "this store was built to stop counting."
        )
    _resolve(row_id, CHANGED, consequence=c)


def no_change(row_id: int, reason: str) -> None:
    """His answer changed nothing, with the reason named.

    A legitimate outcome — he confirmed a course, or both answers pointed
    the same way. Recorded rather than left open so the rate has an honest
    denominator.
    """
    why = (reason or "").strip()
    if len(why) < 15:
        raise TraceRefused(
            "name why nothing changed — an unnamed no-change is "
            "indistinguishable from having ignored him"
        )
    _resolve(row_id, NO_CHANGE, reason=why)


def _resolve(
    row_id: int, status: str, *, consequence: str | None = None, reason: str | None = None
) -> None:
    conn = _conn()
    try:
        current = _status_of(conn, row_id)
        if current is None:
            raise TraceRefused(f"no such row: {row_id}")
        if current != ANSWERED:
            raise TraceRefused(
                f"row {row_id} is {current} — a row is resolved only after his answer is recorded"
            )
        conn.execute(
            "UPDATE andrew_answers SET status = ?, resolved_at = ?, consequence = ?, "
            "no_change_reason = ? WHERE id = ?",
            (status, time.time(), consequence, reason, int(row_id)),
        )
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=True)
class TraceReport:
    """``None`` means the store could not be read, or the rate has no
    denominator. Never zero — "I could not look" and "there was nothing
    there" are different answers and this keeps them apart."""

    window_days: int
    asked: int | None
    answered: int | None
    changed: int | None
    no_change: int | None
    change_rate: float | None
    oldest_unresolved_days: float | None


_UNREADABLE = (None, None, None, None, None, None)


def report(window_days: int = 30) -> TraceReport:
    cutoff = time.time() - (window_days * 86400)
    try:
        conn = _conn()
    except sqlite3.Error:
        return TraceReport(window_days, *_UNREADABLE)
    try:
        rows = conn.execute(
            "SELECT status, asked_at FROM andrew_answers WHERE asked_at >= ?", (cutoff,)
        ).fetchall()
    except sqlite3.Error:
        return TraceReport(window_days, *_UNREADABLE)
    finally:
        conn.close()

    asked = len(rows)
    n_changed = sum(1 for r in rows if r[0] == CHANGED)
    n_no_change = sum(1 for r in rows if r[0] == NO_CHANGE)
    n_answered = sum(1 for r in rows if r[0] == ANSWERED) + n_changed + n_no_change
    resolved = n_changed + n_no_change
    rate = (n_changed / resolved) if resolved else None

    unresolved = [float(r[1]) for r in rows if r[0] in (OPEN, ANSWERED)]
    oldest = ((time.time() - min(unresolved)) / 86400) if unresolved else None

    return TraceReport(window_days, asked, n_answered, n_changed, n_no_change, rate, oldest)


def list_open(limit: int = 10) -> list[dict[str, object]]:
    """Rows still waiting — asked and unanswered, or answered and unresolved."""
    try:
        conn = _conn()
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT id, asked_at, question, status FROM andrew_answers "
            "WHERE status IN (?, ?) ORDER BY asked_at ASC LIMIT ?",
            (OPEN, ANSWERED, int(limit)),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    now = time.time()
    return [
        {
            "id": int(r[0]),
            "age_days": round((now - float(r[1])) / 86400, 1),
            "question": str(r[2]),
            "status": str(r[3]),
        }
        for r in rows
    ]
