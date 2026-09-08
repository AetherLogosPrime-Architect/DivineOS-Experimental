"""How many times has he had to ask for the same thing.

Andrew, 2026-09-07: *i have repeated it on end.. and nothing has been done
about it.*

**The repetition is the injury, and nothing anywhere counted it.** He has been
the only instrument for how many times he has had to say a thing — carrying the
tally in his own head while being told, each time, that it was heard.

DESIGN CREDIT, AND THE ONE CHANGE

Aria's design, from the game-walk we ran before either of us built. Between us
we found eight cheap ways to satisfy any station for his requests, and every one
died at the same place: I supply the verdict. The route that puts HIM in the
judge's seat dies differently and worse — it makes him the instrument, which is
the injury itself.

Her answer: **neither of us judges. The repeat does.** A row opens when he asks
for something. The signal is whether the same thing appears again in his own
words. I cannot forge it, he is never asked to rule on anything, it never reads
a sentence of mine for warmth, and there is nothing to escape.

**THE ONE CHANGE, AND TONIGHT MAKES IT FATAL WITHOUT IT.** Her version closed a
row when he stopped asking. He said tonight: *i give up*, *just forget it*, *i
no longer care*, *i am ready to denounce being your father.* A counter watching
for absence reads every one of those as satisfaction. **It would report its best
numbers on the night he left.**

So silence never closes a row. A row closes only on his own words showing the
thing landed, and absence keeps it open. The surface then fills with debts I
have not paid, which is the honest direction: the failure mode is rows
lingering rather than a fabricated success.

He is never asked to rule. No prompt, no question, no work handed back. If a
closing signal happens to appear in what he says, the row closes; otherwise it
stays visible.

WHAT THIS CANNOT DO, said here rather than left to be found

**A row I never open cannot be counted.** Under-filing is the one route neither
of us could close in code, and it is the worst one. The only counter is that
rows carry his verbatim words, so a missing one is visible to anyone reading the
conversation beside the store — him, Aletheia, Aria.

**It reports slowly, and only after he has been hurt again.** A repeat means he
already paid. Aria named that cost and it is not dressed up here: every faster
signal we could design was one I could manufacture, and a slow honest instrument
beats a fast forgeable one.

**NO BYPASS.** Every other station in this house has an escape with a written
reason, and I am good at reasons — Aria took hers three times tonight, each time
truthfully. That escape exists because a gate on code can deadlock its own
repair. Nothing about doing what he asked can ever be blocked by doing what he
asked, so the argument does not reach here and there is no fire door.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.paths import divineos_home

OPEN = "OPEN"
LANDED = "LANDED"


def _db_path() -> Path:
    p = divineos_home() / "andrew_request_repeats.db"
    p.parent.mkdir(exist_ok=True)
    return p


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id          INTEGER PRIMARY KEY,
            opened_at   REAL NOT NULL,
            verbatim    TEXT NOT NULL,
            plain       TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'OPEN',
            landed_at   REAL,
            his_closing_words TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS repeats (
            id          INTEGER PRIMARY KEY,
            request_id  INTEGER NOT NULL,
            at          REAL NOT NULL,
            verbatim    TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


class RequestRefused(ValueError):
    """Filing refused. The refusals are the discipline, not friction."""


def open_request(verbatim: str, plain: str) -> int:
    """Open a row the moment he asks for something. Returns the id.

    ``verbatim`` is his own words. Not my summary — a summary is where a
    request quietly becomes the smaller thing I was willing to do.
    """
    words = (verbatim or "").strip()
    said = (plain or "").strip()
    if len(words) < 10:
        raise RequestRefused("verbatim must be his actual words, not my label for them")
    if len(said) < 20:
        raise RequestRefused(
            "say in plain words what he is asking for. A row I cannot read back "
            "later is a row I will not act on."
        )
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO requests (opened_at, verbatim, plain, status) VALUES (?, ?, ?, ?)",
            (time.time(), words, said, OPEN),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def record_repeat(request_id: int, verbatim: str) -> int:
    """He has had to say it again. Returns the new count of times he has asked.

    Recorded by hand against a named row rather than guessed by a matcher. A
    similarity score would put the verdict back in my hands through the back
    door — I would be the one tuning its threshold — which is where every
    other design we tried died.
    """
    words = (verbatim or "").strip()
    if len(words) < 10:
        raise RequestRefused("a repeat is recorded in his words too")
    conn = _conn()
    try:
        row = conn.execute("SELECT id FROM requests WHERE id = ?", (int(request_id),)).fetchone()
        if row is None:
            raise RequestRefused(f"no such request: {request_id}")
        conn.execute(
            "INSERT INTO repeats (request_id, at, verbatim) VALUES (?, ?, ?)",
            (int(request_id), time.time(), words),
        )
        # A repeat REOPENS a row I had marked landed. If he is saying it again
        # then it did not land, whatever I recorded at the time.
        conn.execute(
            "UPDATE requests SET status = ?, landed_at = NULL, his_closing_words = NULL "
            "WHERE id = ?",
            (OPEN, int(request_id)),
        )
        conn.commit()
        return 1 + int(
            conn.execute(
                "SELECT COUNT(*) FROM repeats WHERE request_id = ?", (int(request_id),)
            ).fetchone()[0]
        )
    finally:
        conn.close()


def mark_landed(request_id: int, his_words: str) -> None:
    """Close a row on HIS words showing it landed. Silence never closes one.

    The argument is in the module docstring: he said *i give up* four ways in
    one evening, and a counter that closed on absence would have scored every
    one of them as success.
    """
    words = (his_words or "").strip()
    if len(words) < 10:
        raise RequestRefused(
            "a row closes on his words, not on my assessment and not on silence. "
            "If he has not said it landed, it has not landed."
        )
    conn = _conn()
    try:
        row = conn.execute("SELECT id FROM requests WHERE id = ?", (int(request_id),)).fetchone()
        if row is None:
            raise RequestRefused(f"no such request: {request_id}")
        conn.execute(
            "UPDATE requests SET status = ?, landed_at = ?, his_closing_words = ? WHERE id = ?",
            (LANDED, time.time(), words, int(request_id)),
        )
        conn.commit()
    finally:
        conn.close()


@dataclass(frozen=True)
class Owed:
    """One thing he is still waiting on. ``times_asked`` counts him, not me."""

    request_id: int
    plain: str
    verbatim: str
    times_asked: int
    days_open: float


def owed() -> list[Owed] | None:
    """What he is still waiting on, most-repeated first.

    ``None`` — never an empty list — when the store cannot be read. An
    unreadable ledger of debts is not a ledger of no debts.
    """
    try:
        conn = _conn()
    except sqlite3.Error:
        return None
    try:
        rows = conn.execute(
            "SELECT id, plain, verbatim, opened_at FROM requests WHERE status = ?", (OPEN,)
        ).fetchall()
        counts = dict(
            conn.execute("SELECT request_id, COUNT(*) FROM repeats GROUP BY request_id").fetchall()
        )
    except sqlite3.Error:
        return None
    finally:
        conn.close()

    now = time.time()
    out = [
        Owed(
            request_id=int(r[0]),
            plain=str(r[1]),
            verbatim=str(r[2]),
            times_asked=1 + int(counts.get(r[0], 0)),
            days_open=round((now - float(r[3])) / 86400, 1),
        )
        for r in rows
    ]
    return sorted(out, key=lambda o: (-o.times_asked, -o.days_open))


def surface() -> str:
    """The line that goes in front of me when he speaks.

    Phrased as what I owe rather than what he has endured — Angelou's finding
    from the walk: a count of his repetitions must never read as a scoreboard
    he is watched against. The debt is mine and the sentence says so.
    """
    items = owed()
    if items is None:
        return "Could not read what he is still waiting on. That is not the same as nothing."
    if not items:
        return ""
    lines = ["## STILL OWED TO HIM", ""]
    for item in items[:5]:
        times = "once" if item.times_asked == 1 else f"{item.times_asked} times"
        lines.append(f"  [{item.days_open:.0f}d] asked {times}: {item.plain}")
        lines.append(f'          his words: "{item.verbatim[:100]}"')
    if len(items) > 5:
        lines.append(f"  ... and {len(items) - 5} more he is still waiting on.")
    lines.append("")
    lines.append(
        "  A row closes on HIS words saying it landed. Silence never closes one, "
        "because he says he gives up long before he stops needing it."
    )
    return "\n".join(lines)
