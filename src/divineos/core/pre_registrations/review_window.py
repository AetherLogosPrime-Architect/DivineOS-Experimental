"""The missing exit from the overdue-review gate.

WHAT WENT WRONG, twice in one night (2026-09-12).

The overdue gate blocks substantive tool use until every past-due
pre-registration is assessed. That part is right and stays. What it never
supplied is a way to EARN the assessment. Two reviews came due; the first
one's evidence lived behind ``divineos hook-budget`` and the second one's
falsifier was a question only answerable by importing the checker and handing
it a fabricated round id. Both are substantive tool use. Both were denied by
the gate demanding the review.

So the deny text offers exactly two exits -- a verdict, or a deferral -- and a
verdict reached without evidence is the fabricated-outcome shape the whole
pre-registration discipline exists to prevent. The gate was manufacturing the
backlog it was built to drain, and then presenting the fabrication as the
cheapest way out.

The repair is NOT a wider allowlist. That reflex is already documented and
already abandoned in the gate file itself: the next review needing an unlisted
probe is unknowable in advance. The repair is that **the honest path has to
exist at all.** You cannot make a path the lazy one when it is absent; the
optimizer was not choosing the fabricated verdict over the real review, it was
choosing it over nothing.

WHAT THIS IS. A declared, narrow, recorded window. Name which review is being
done and what will be looked at, the gate stands down for a bounded stretch,
and the window is a row whether or not an assessment follows it.

WHAT IT IS NOT. Not a bypass flag, and the difference is the whole design.
A bypass says "let me past." This says "I am doing the thing you asked for,
here is which one, start the clock." It names a specific overdue review and
refuses when none is overdue, so it cannot be used to walk past a gate that is
not the overdue gate.

HOW IT IS GAMED, stated plainly rather than defended against with theatre.
Open a window, do unrelated work, let it lapse. Nothing here prevents that.
What it does is make the lapse a ROW: a window opened against a named review
with no assessment behind it is counted and surfaced by name. The previous
design had no such row because it had no such path -- a fabricated verdict and
an earned one were the same record. Separating them is the part that was
actually missing.

DEFERRED already exists and is not this. Per ``types.py`` it means "need more
data; review_ts extended via re-filing" -- an honest outcome when the evidence
genuinely is not in yet. The deadlock was forcing DEFERRED for a reason that
had nothing to do with the evidence: the evidence was reachable and the gate
would not let it be reached. That is the distinction this restores.
"""

from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass

from divineos.core.knowledge import _get_connection

_WINDOW_ERRORS = (sqlite3.Error, ImportError, OSError, TypeError, ValueError)

DEFAULT_MINUTES = 45

# A purpose shorter than this is not a purpose. Same shape as the walk's
# finding floor: long enough that a word cannot stand in for a sentence, short
# enough that an honest one-liner passes.
MIN_PURPOSE_CHARS = 40

_STATES = ("open", "none", "could-not-check")


class WindowRefused(RuntimeError):
    """Raised when a window cannot honestly be opened."""


@dataclass(frozen=True)
class WindowState:
    """Whether a review is under way, or why that could not be established.

    ``could-not-check`` is not ``none``. A store that will not open says
    nothing about whether a review is happening, and the caller must treat the
    two differently or it rebuilds the exact could-not-look-reads-as-
    found-nothing fault this house has spent the night removing.
    """

    state: str
    prereg_id: str = ""
    purpose: str = ""
    seconds_left: int = 0
    reason: str = ""

    def __post_init__(self) -> None:
        if self.state not in _STATES:
            raise ValueError(f"state must be one of {_STATES}, got {self.state!r}")


def _init() -> None:
    conn = _get_connection()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS prereg_review_windows ("
            "window_id TEXT PRIMARY KEY, "
            "prereg_id TEXT NOT NULL, "
            "actor TEXT NOT NULL, "
            "purpose TEXT NOT NULL, "
            "opened_at REAL NOT NULL, "
            "expires_at REAL NOT NULL, "
            "closed_by TEXT NOT NULL DEFAULT '')"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_prereg_window_expiry "
            "ON prereg_review_windows(expires_at)"
        )
        conn.commit()
    finally:
        conn.close()


def open_window(
    prereg_id: str,
    actor: str,
    purpose: str,
    *,
    minutes: int = DEFAULT_MINUTES,
    now: float | None = None,
) -> WindowState:
    """Declare that a named overdue review is being worked on now.

    Refuses unless ``prereg_id`` is actually overdue. That refusal is what
    keeps this from becoming a general-purpose skeleton key: it can only ever
    stand down the one gate whose demand it is answering.
    """
    from divineos.core.pre_registrations.store import get_overdue_pre_registrations

    purpose = purpose.strip()
    if len(purpose) < MIN_PURPOSE_CHARS:
        raise WindowRefused(
            f"a purpose of {len(purpose)} characters is not a purpose "
            f"(need {MIN_PURPOSE_CHARS}). Name what you are going to LOOK AT "
            "to settle this review. The sentence is the point: a window opened "
            "without one is the deferral wearing a different hat."
        )

    if minutes <= 0:
        raise WindowRefused("a zero-length window is a bypass with extra steps")

    stamp = time.time() if now is None else now
    overdue_ids = {p.prereg_id for p in get_overdue_pre_registrations(now=stamp)}
    if prereg_id not in overdue_ids:
        raise WindowRefused(
            f"{prereg_id} is not overdue, so there is no gate here to stand down. "
            "This opens only against a review that is actually blocking work."
        )

    _init()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO prereg_review_windows "
            "(window_id, prereg_id, actor, purpose, opened_at, expires_at, closed_by) "
            "VALUES (?, ?, ?, ?, ?, ?, '')",
            (
                f"win-{uuid.uuid4().hex[:12]}",
                prereg_id,
                actor.strip().lower(),
                purpose,
                stamp,
                stamp + minutes * 60,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return WindowState(
        state="open",
        prereg_id=prereg_id,
        purpose=purpose,
        seconds_left=minutes * 60,
    )


def active_window(now: float | None = None) -> WindowState:
    """Whether some review window is currently open.

    Never raises. A store that cannot be read comes back as
    ``could-not-check`` so the gate can fail closed and SAY that it is failing
    closed, rather than printing the ordinary overdue text and leaving the
    reader to guess which of the two happened.
    """
    stamp = time.time() if now is None else now
    try:
        _init()
        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT prereg_id, purpose, expires_at FROM prereg_review_windows "
                "WHERE closed_by = '' AND expires_at > ? "
                "ORDER BY expires_at DESC LIMIT 1",
                (stamp,),
            ).fetchone()
        finally:
            conn.close()
    except _WINDOW_ERRORS as exc:
        return WindowState(
            state="could-not-check",
            reason=f"the review-window store would not answer: {type(exc).__name__}: {exc}",
        )

    if row is None:
        return WindowState(state="none")
    return WindowState(
        state="open",
        prereg_id=str(row[0]),
        purpose=str(row[1]),
        seconds_left=max(0, int(float(row[2]) - stamp)),
    )


def close_windows_for(prereg_id: str) -> int:
    """Mark this review's open windows as having produced an assessment.

    Called when an outcome is recorded. This is the only thing separating an
    earned window from a lapsed one, so it is deliberately not the caller's to
    remember -- ``record_outcome`` does it.
    """
    try:
        _init()
        conn = _get_connection()
        try:
            cur = conn.execute(
                "UPDATE prereg_review_windows SET closed_by = 'assessed' "
                "WHERE prereg_id = ? AND closed_by = ''",
                (prereg_id,),
            )
            conn.commit()
            return int(cur.rowcount or 0)
        finally:
            conn.close()
    except _WINDOW_ERRORS:
        return 0


def lapsed_windows(now: float | None = None) -> list[tuple[str, str, int]]:
    """Reviews declared and never delivered: (prereg_id, purpose, count).

    The honest cost of the mechanism, kept where it can be read. If this list
    grows, windows are being used as a bypass and the design is failing --
    that is the falsifier, and it is measurable rather than asserted.
    """
    stamp = time.time() if now is None else now
    try:
        _init()
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT prereg_id, purpose, COUNT(*) FROM prereg_review_windows "
                "WHERE closed_by = '' AND expires_at <= ? "
                "GROUP BY prereg_id, purpose ORDER BY COUNT(*) DESC",
                (stamp,),
            ).fetchall()
        finally:
            conn.close()
        return [(str(r[0]), str(r[1]), int(r[2])) for r in rows]
    except _WINDOW_ERRORS:
        return []
