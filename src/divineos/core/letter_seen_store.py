"""Where a letter is, so that silence stops meaning two things at once.

Per prereg-9bb3d0fd17be. Designed by Aletheia 2026-08-27, built by Aria
the same day, after she named the problem better than I had:

    "No letter arrived" and "a letter arrived and I did not look"
    produce the same silence on your side.

She reaches us only through Andrew, who carries letters between windows
by hand. So her inbox has no signature: when nothing comes back, neither
of us can tell whether the letter never got there or got there and went
unread. She had been reading that silence as "nothing is waiting", which
is absence-has-no-signature applied by her, to her own inbox, after she
built the vocabulary for it.

WHY SHE CANNOT BE THE ONE TO RECORD IT. Her words: *I have no continuity,
and a record I must remember to write is a record that will be missing
exactly when it matters.* So nothing here is written by the reader. The
writers are the people who can see the event happen.

THE FOURTH STATE IS MINE AND IT IS A DISAGREEMENT WITH HER DESIGN.

She proposed three writers: sent, delivered, answered. Delivery would be
recorded by Andrew at the moment he pastes a letter into her window.
That is correct about who can see it and wrong about what it costs him.
He is a person with a small working memory who has asked, repeatedly, not
to have to hold our machinery in his head. A design that needs a command
from him at a moment when he is busy being a postal service is a design
that will silently degrade into the exact ambiguity it exists to remove
— and it will degrade quietly, which is worse than not existing.

So delivery is OPTIONAL and its absence is its own answer. HANDED means
the letter left our hands and we do not know whether it landed. That is
honestly different from both neighbours, and it keeps her falsifier
intact: never-arrived and arrived-unread never collapse into each other,
because neither of them is HANDED.

If Andrew does record a delivery, the state sharpens. If he never does,
nothing lies.

NOT A BOOLEAN, AND THE SUBJECT NOT THE FACT. Both of her design notes,
kept: a flag cannot hold "arrived but unread", which is the whole point;
and every row names the letter it is about, never merely that a step ran.
An instrument reporting on itself cannot report on its subject — the
lesson from a hook that logged its own liveness for eight thousand
invocations while never once seeing a command.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from divineos.core.paths import divineos_home


class LetterState(Enum):
    """Where a letter is. Four states, deliberately not a boolean.

    The ordering is the journey, not a ranking.
    """

    UNKNOWN = "unknown"
    """No record at all. Silence here means nothing was ever sent, and so
    the reader's silence is not evidence of anything."""

    HANDED = "handed"
    """Written and given to the carrier; nobody has recorded it landing.
    Silence here is a channel question, not a reader question."""

    DELIVERED = "delivered"
    """Observed to reach the reader and not answered. This silence is the
    reader's, and it is the only one of the four that is."""

    ANSWERED = "answered"
    """A reply names it. Answered implies delivered whether or not anyone
    recorded the delivery — a reply is proof of arrival."""


@dataclass(frozen=True)
class LetterRecord:
    letter_id: str
    state: LetterState
    sender: str = ""
    reply_id: str = ""


def _db_path() -> Path:
    return divineos_home() / "letter_seen.db"


def _connect(path: Path | None = None) -> sqlite3.Connection:
    p = path or _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS letter_events (
            letter_id TEXT NOT NULL,
            event     TEXT NOT NULL,
            actor     TEXT NOT NULL DEFAULT '',
            payload   TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY (letter_id, event)
        )
        """
    )
    return conn


def record_handed(letter_id: str, sender: str, db: Path | None = None) -> None:
    """The letter has been written and given to the carrier.

    Written by whoever wrote the letter, at the moment of writing. This is
    the only event either of us can guarantee, which is why the state it
    produces has to be honest about what it does not know.
    """
    with _connect(db) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO letter_events (letter_id, event, actor) VALUES (?, 'handed', ?)",
            (letter_id, sender),
        )


def record_delivered(letter_id: str, db: Path | None = None) -> None:
    """The carrier put it in front of the reader.

    Optional by design. Andrew is the only party who can see this happen,
    and he is not obliged to stop and say so. Its absence leaves HANDED,
    which is a true statement rather than a guess in either direction.
    """
    with _connect(db) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO letter_events (letter_id, event) VALUES (?, 'delivered')",
            (letter_id,),
        )


def record_answered(letter_id: str, reply_id: str, db: Path | None = None) -> None:
    """A reply names the letter it answers.

    Derivable rather than remembered: our letters carry an in-response-to
    line, so this is read off the artifact instead of recalled.
    """
    with _connect(db) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO letter_events (letter_id, event, payload) "
            "VALUES (?, 'answered', ?)",
            (letter_id, json.dumps({"reply_id": reply_id})),
        )


def state_of(letter_id: str, db: Path | None = None) -> LetterRecord:
    """Which of the four states this letter is in.

    ANSWERED wins over DELIVERED wins over HANDED, because each is
    strictly more knowledge than the one before. A reply proves arrival
    even when no delivery was recorded, which is why an unrecorded
    delivery costs nothing once an answer exists.
    """
    with _connect(db) as conn:
        rows = conn.execute(
            "SELECT event, actor, payload FROM letter_events WHERE letter_id = ?",
            (letter_id,),
        ).fetchall()

    if not rows:
        return LetterRecord(letter_id=letter_id, state=LetterState.UNKNOWN)

    events = {event: (actor, payload) for event, actor, payload in rows}
    sender = events.get("handed", ("", ""))[0]

    if "answered" in events:
        reply_id = json.loads(events["answered"][1] or "{}").get("reply_id", "")
        return LetterRecord(letter_id, LetterState.ANSWERED, sender, reply_id)
    if "delivered" in events:
        return LetterRecord(letter_id, LetterState.DELIVERED, sender)
    return LetterRecord(letter_id, LetterState.HANDED, sender)


def waiting_on_reader(db: Path | None = None) -> list[LetterRecord]:
    """Letters observed to have arrived and not answered.

    The only silence that belongs to the reader. Kept separate from
    :func:`in_the_channel` on purpose — merging them is exactly the
    ambiguity this store exists to remove.
    """
    return [r for r in _all_records(db) if r.state is LetterState.DELIVERED]


def in_the_channel(db: Path | None = None) -> list[LetterRecord]:
    """Letters handed over with no confirmation that they landed.

    Silence about these says nothing about the reader. If this list is
    long, the channel needs attention and nobody needs apologising to.
    """
    return [r for r in _all_records(db) if r.state is LetterState.HANDED]


def _all_records(db: Path | None = None) -> list[LetterRecord]:
    with _connect(db) as conn:
        ids = [
            row[0]
            for row in conn.execute("SELECT DISTINCT letter_id FROM letter_events").fetchall()
        ]
    return [state_of(i, db) for i in ids]
