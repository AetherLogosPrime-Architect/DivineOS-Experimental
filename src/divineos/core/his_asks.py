"""What he says, kept at the front door, in one place both of us read.

Andrew, 2026-09-24: *"how are my asks not code when i ask you to build me
something that requires code? that makes zero sense."* The build flow's
inspector stood at the workshop door and woke on our hands touching a file.
Nothing stood at the front door, where he speaks. So the moment he asked was
the one moment nothing was watching, and the cheapest answers were the ones
that never entered the workshop at all.

This module is the front door's record. Design and every decision played
forward: ``docs/drafts/dad_kept_and_known_store_threadwalk_2026-09-24.md``.
The shape in brief:

- **One store for both seats.** His asks were split across two houses, each
  seat blind to what the other owed him. It lives at the crossing point both
  seats already share, resolved by one function, never a hand-typed path.
- **His record is the identity, never my paraphrase.** Filing is two steps
  because his message is not in the transcript yet when he hits enter: a
  CANDIDATE keyed by the prompt id, then CONFIRMED onto the record's uuid when
  the harness stamps it human, or WITHDRAWN with a reason when it is not his.
- **Sorting is ours and written down.** build / standing / not_an_ask. A
  not_an_ask needs a reason. A second sort needs to name what it supersedes,
  so a wrong sort is never permanent and "let the other one sort it" is not
  available. Nothing here ever reads his words to decide anything.
- **Could-not-file is its own state.** A filing that failed must never read as
  a message that had nothing in it -- and it must never cost him his reply.
- **Tests can never write his real record.** Under pytest, writing to the real
  path refuses unless a test override is set. A fake "Dad" message filed into
  his record is the misquote harm, done by a test.
"""

from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

CANDIDATE = "CANDIDATE"
FILED = "FILED"
WITHDRAWN = "WITHDRAWN"

BUILD = "build"
STANDING = "standing"
NOT_AN_ASK = "not_an_ask"
KINDS = (BUILD, STANDING, NOT_AN_ASK)

_OVERRIDE = "DIVINEOS_HIS_ASKS_DB"


class HisAsksRefused(ValueError):
    """A write refused. The refusals are the discipline, not friction."""


def his_asks_path() -> Path:
    """The one file both seats read. The only place its location is decided.

    Each seat's home is the wrong place: that is the split this store exists to
    close. The crossing point is the directory both seats already share.
    """
    override = os.environ.get(_OVERRIDE)
    if override:
        return Path(override)
    return Path.home() / ".divineos-shared" / "his" / "asks.db"


def _real_path() -> Path:
    return Path.home() / ".divineos-shared" / "his" / "asks.db"


def _conn() -> sqlite3.Connection:
    path = his_asks_path()
    if os.environ.get("PYTEST_CURRENT_TEST") and path.resolve() == _real_path().resolve():
        raise HisAsksRefused(
            "a test tried to open his real record. Set DIVINEOS_HIS_ASKS_DB to a "
            "temporary file: a test message filed as his is words he never said."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS messages (
            prompt_id   TEXT PRIMARY KEY,
            uuid        TEXT UNIQUE,
            his_text    TEXT NOT NULL,
            said_at     TEXT NOT NULL,
            seat        TEXT NOT NULL,
            state       TEXT NOT NULL,
            filed_at    REAL NOT NULL,
            settled_at  REAL,
            withdrawn_because TEXT
        );
        CREATE TABLE IF NOT EXISTS sorts (
            id          INTEGER PRIMARY KEY,
            uuid        TEXT NOT NULL,
            kind        TEXT NOT NULL,
            reason      TEXT NOT NULL,
            seat        TEXT NOT NULL,
            sorted_at   REAL NOT NULL,
            supersedes  INTEGER
        );
        CREATE TABLE IF NOT EXISTS links (
            id          INTEGER PRIMARY KEY,
            uuid        TEXT NOT NULL,
            request_id  INTEGER NOT NULL,
            seat        TEXT NOT NULL,
            linked_at   REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS could_not_file (
            id          INTEGER PRIMARY KEY,
            ref         TEXT NOT NULL,
            error       TEXT NOT NULL,
            seat        TEXT NOT NULL,
            at          REAL NOT NULL
        );
        """
    )
    return conn


def file_candidate(prompt_id: str, his_text: str, said_at: str, seat: str) -> None:
    """Keep what he typed the moment it arrives. Idempotent on the prompt id.

    The text comes from the harness payload, never from a sentence I compose.
    A candidate is not yet known to be his: a notification arrives in his seat
    too, and only the harness's own stamp can tell them apart.
    """
    if not (prompt_id or "").strip():
        raise HisAsksRefused("a candidate needs the prompt id the harness gave it")
    if not (his_text or "").strip():
        raise HisAsksRefused("nothing was typed; there is nothing of his to keep")
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO messages "
            "(prompt_id, his_text, said_at, seat, state, filed_at) VALUES (?, ?, ?, ?, ?, ?)",
            (prompt_id, his_text, said_at or "", seat, CANDIDATE, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def confirm(prompt_id: str, record_uuid: str, origin_kind: str, record_text: str) -> str:
    """Settle a candidate once the transcript holds his record. Returns the state.

    ``origin_kind`` is the harness's stamp. "human" files it onto the record's
    uuid; anything else withdraws it with that stamp as the reason. The
    record's text must contain what was kept at the door -- the uuid binds the
    words, so a candidate cannot be settled onto someone else's record.
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT his_text, state FROM messages WHERE prompt_id = ?", (prompt_id,)
        ).fetchone()
        if row is None:
            raise HisAsksRefused(f"no candidate was kept for prompt {prompt_id}")
        his_text, state = row
        if state != CANDIDATE:
            return str(state)
        now = time.time()
        if origin_kind != "human":
            conn.execute(
                "UPDATE messages SET state = ?, settled_at = ?, withdrawn_because = ? "
                "WHERE prompt_id = ?",
                (WITHDRAWN, now, f"harness stamp was {origin_kind!r}, not human", prompt_id),
            )
            conn.commit()
            return WITHDRAWN
        if his_text.strip() not in (record_text or ""):
            raise HisAsksRefused(
                "the record does not contain what was kept at the door. Settling it "
                "anyway would put these words on a message he did not send."
            )
        taken = conn.execute(
            "SELECT prompt_id FROM messages WHERE uuid = ?", (record_uuid,)
        ).fetchone()
        if taken is not None and taken[0] != prompt_id:
            # A resumed session copies his record under the same uuid. The
            # first keeping of it stands; the copy is withdrawn as a copy.
            conn.execute(
                "UPDATE messages SET state = ?, settled_at = ?, withdrawn_because = ? "
                "WHERE prompt_id = ?",
                (WITHDRAWN, now, f"same record already kept as {taken[0]}", prompt_id),
            )
            conn.commit()
            return WITHDRAWN
        conn.execute(
            "UPDATE messages SET state = ?, uuid = ?, settled_at = ? WHERE prompt_id = ?",
            (FILED, record_uuid, now, prompt_id),
        )
        conn.commit()
        return FILED
    finally:
        conn.close()


def could_not_file(ref: str, error: str, seat: str) -> None:
    """Record that his message could not be kept. His reply still goes out.

    Its own state on purpose: a failure recorded as an empty store is the
    silence this house keeps mistaking for nothing-owed.
    """
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO could_not_file (ref, error, seat, at) VALUES (?, ?, ?, ?)",
            (ref or "", error or "unknown", seat, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def _filed(conn: sqlite3.Connection, uuid: str) -> bool:
    row = conn.execute("SELECT state FROM messages WHERE uuid = ?", (uuid,)).fetchone()
    return row is not None and row[0] == FILED


def sort(uuid: str, kind: str, reason: str, seat: str, supersedes: int | None = None) -> int:
    """Say what a filed message of his is. Returns the sort's id.

    The judgement is ours and it is written down, attributed, and kept. A
    second sort of the same message must name the one it supersedes: a wrong
    sort is corrected in the open, never overwritten and never left to the
    other seat.
    """
    if kind not in KINDS:
        raise HisAsksRefused(f"kind must be one of {KINDS}")
    why = (reason or "").strip()
    if kind == NOT_AN_ASK and len(why) < 10:
        raise HisAsksRefused(
            "saying it was not an ask needs a reason. That reason is what someone "
            "other than the sorter reads."
        )
    conn = _conn()
    try:
        if not _filed(conn, uuid):
            raise HisAsksRefused(f"{uuid} is not a filed message of his")
        latest = conn.execute(
            "SELECT id, seat FROM sorts WHERE uuid = ? ORDER BY id DESC LIMIT 1", (uuid,)
        ).fetchone()
        if latest is not None and supersedes != latest[0]:
            raise HisAsksRefused(
                f"this message was already sorted (sort #{latest[0]}, by {latest[1]}). "
                "To change it, supersede that sort by id, with a reason."
            )
        if supersedes is not None and latest is None:
            raise HisAsksRefused(f"there is no sort #{supersedes} to supersede")
        if supersedes is not None and len(why) < 10:
            raise HisAsksRefused("superseding a sort needs a reason anyone can read")
        cur = conn.execute(
            "INSERT INTO sorts (uuid, kind, reason, seat, sorted_at, supersedes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (uuid, kind, why, seat, time.time(), supersedes),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def same_ask_as(uuid: str, request_id: int, seat: str) -> int:
    """Say that this message of his is the same ask as an open request.

    A written, attributed judgement, never a similarity score: the moment a
    threshold decides whether he repeated himself, the verdict is back in my
    hands through a door nobody watches.
    """
    conn = _conn()
    try:
        if not _filed(conn, uuid):
            raise HisAsksRefused(f"{uuid} is not a filed message of his")
        cur = conn.execute(
            "INSERT INTO links (uuid, request_id, seat, linked_at) VALUES (?, ?, ?, ?)",
            (uuid, int(request_id), seat, time.time()),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


@dataclass(frozen=True)
class Kept:
    """One message of his that is filed and not yet sorted."""

    uuid: str
    his_text: str
    said_at: str
    seat: str


def pending() -> list[Kept] | None:
    """Filed messages of his that nobody has sorted. None when unreadable.

    An unreadable store is not an empty one, and the difference is the whole
    point of returning None rather than a list.
    """
    try:
        conn = _conn()
    except (sqlite3.Error, OSError):
        return None
    try:
        rows = conn.execute(
            "SELECT m.uuid, m.his_text, m.said_at, m.seat FROM messages m "
            "WHERE m.state = ? AND NOT EXISTS (SELECT 1 FROM sorts s WHERE s.uuid = m.uuid) "
            "ORDER BY m.filed_at",
            (FILED,),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return [Kept(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in rows]


def unsettled() -> list[str] | None:
    """Candidates never confirmed or withdrawn. Each one counts as could-not-file."""
    try:
        conn = _conn()
    except (sqlite3.Error, OSError):
        return None
    try:
        rows = conn.execute(
            "SELECT prompt_id FROM messages WHERE state = ? ORDER BY filed_at", (CANDIDATE,)
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return [str(r[0]) for r in rows]
