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
  CANDIDATE keyed by an id minted at the door (never the prompt id alone, which
  many of his messages share), then CONFIRMED onto the record's uuid when
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

import hashlib
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from divineos.core.harness_envelopes import nothing_of_his

CANDIDATE = "CANDIDATE"
FILED = "FILED"
WITHDRAWN = "WITHDRAWN"
# Kept at the door in his words, and the transcript record that confirms who
# typed them was never found. Not WITHDRAWN (that means "not his") and not
# FILED. Read by pending() like a filed message, so it is never lost for the
# failure of our instrument (2026-09-24, walk-2592439477f9).
UNMATCHED = "UNMATCHED"

# Who put what-we-sent-before on record: the door, reading the transcript, or
# the sorter quoting it because the door could not. Never passed off as each
# other.
CAPTURED = "captured"
SORTER = "sorter"

BUILD = "build"
STANDING = "standing"
NOT_AN_ASK = "not_an_ask"
KINDS = (BUILD, STANDING, NOT_AN_ASK)

# Who he said it to. Andrew, 2026-09-24: "if you are making a shared copy for
# both of you then it needs to have some form of attribution, who it was said
# to, or if its a general thing you can both share, or it may get confusing if
# you are reading every thing as spoken to you". Named absolutely, never "this
# seat": the store is shared, so a relative word would mean opposite things to
# the two readers.
ADDRESSEES = ("aria", "aether", "both")

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
            candidate_id TEXT PRIMARY KEY,
            prompt_id   TEXT NOT NULL,
            uuid        TEXT UNIQUE,
            his_text    TEXT NOT NULL,
            said_at     TEXT NOT NULL,
            seat        TEXT NOT NULL,
            state       TEXT NOT NULL,
            filed_at    REAL NOT NULL,
            settled_at  REAL,
            withdrawn_because TEXT
        );
        -- sorts.uuid and links.uuid hold the SORT ID: his record's uuid, or,
        -- for an UNMATCHED message, its candidate id. Declared here rather than
        -- migrated (Dijkstra on walk-2592439477f9); every signature calls it
        -- sort_id so no reader takes a candidate id for a transcript uuid.
        CREATE TABLE IF NOT EXISTS sorts (
            id          INTEGER PRIMARY KEY,
            uuid        TEXT NOT NULL,
            kind        TEXT NOT NULL,
            reason      TEXT NOT NULL,
            seat        TEXT NOT NULL,
            addressed_to TEXT NOT NULL,
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
        -- Why a message was given up on. Its own table, so a store both seats
        -- already opened needs no ALTER that the two could race on.
        CREATE TABLE IF NOT EXISTS unmatched (
            candidate_id TEXT PRIMARY KEY,
            because     TEXT NOT NULL,
            at          REAL NOT NULL
        );
        -- What we sent him right before a message of his. Written once per
        -- message (the primary key refuses a second), by the door (captured)
        -- or, when the door could not, by the sorter (sorter). See sent_before().
        CREATE TABLE IF NOT EXISTS sent_before (
            candidate_id TEXT PRIMARY KEY,
            text        TEXT NOT NULL,
            source      TEXT NOT NULL,
            at          REAL NOT NULL
        );
        """
    )
    return conn


def mint_candidate_id(prompt_id: str, his_text: str, arrived_at: str) -> str:
    """The identity a message of his gets at the door, before any record exists.

    NOT the prompt id alone. Measured by Aether, 2026-09-24: one prompt id sat
    on ten of his messages across eight hours, because a message he sends
    while we are mid-turn fires the prompt hook with the RUNNING turn's id.
    Keyed on that, the store kept his first message per id and silently
    dropped the rest -- the exact failure this store exists to stop. The prompt
    id stays, but only as a hint for finding his record.
    """
    material = f"{prompt_id}\x00{arrived_at}\x00{his_text}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()[:24]


def file_candidate(
    candidate_id: str, prompt_id: str, his_text: str, said_at: str, seat: str
) -> None:
    """Keep what he typed the moment it arrives. Idempotent on the candidate id.

    The text comes from the harness payload, never from a sentence I compose.
    A candidate is not yet known to be his: a notification arrives in his seat
    too, and only the harness's own stamp can tell them apart.
    """
    if not (candidate_id or "").strip():
        raise HisAsksRefused("a candidate needs the id minted for it at the door")
    if not (his_text or "").strip():
        raise HisAsksRefused("nothing was typed; there is nothing of his to keep")
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO messages "
            "(candidate_id, prompt_id, his_text, said_at, seat, state, filed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (candidate_id, prompt_id or "", his_text, said_at or "", seat, CANDIDATE, time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def confirm(
    candidate_id: str,
    record_uuid: str,
    origin_kind: str,
    record_text: str,
    *,
    sent_before: str | None = None,
) -> str:
    """Settle a candidate once the transcript holds his record. Returns the state.

    ``origin_kind`` is the harness's stamp. "human" files it onto the record's
    uuid; anything else withdraws it with that stamp as the reason. The
    record's text must contain what was kept at the door -- the uuid binds the
    words, so a candidate cannot be settled onto someone else's record.

    ``sent_before`` is our last text to him ahead of his record, which the door
    reads from the transcript. Kept whole, as captured. See sent_before().
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT his_text, state FROM messages WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise HisAsksRefused(f"no candidate was kept as {candidate_id}")
        his_text, state = row
        if state != CANDIDATE:
            return str(state)
        now = time.time()
        if origin_kind != "human":
            conn.execute(
                "UPDATE messages SET state = ?, settled_at = ?, withdrawn_because = ? "
                "WHERE candidate_id = ?",
                (WITHDRAWN, now, f"harness stamp was {origin_kind!r}, not human", candidate_id),
            )
            conn.commit()
            return WITHDRAWN
        if his_text.strip() not in (record_text or ""):
            raise HisAsksRefused(
                "the record does not contain what was kept at the door. Settling it "
                "anyway would put these words on a message he did not send."
            )
        taken = conn.execute(
            "SELECT candidate_id FROM messages WHERE uuid = ?", (record_uuid,)
        ).fetchone()
        if taken is not None and taken[0] != candidate_id:
            # Two candidates are never bound to one record. A resumed session
            # copies his record under the same uuid; the first keeping of it
            # stands and the copy is withdrawn as a copy.
            conn.execute(
                "UPDATE messages SET state = ?, settled_at = ?, withdrawn_because = ? "
                "WHERE candidate_id = ?",
                (WITHDRAWN, now, f"same record already kept as {taken[0]}", candidate_id),
            )
            conn.commit()
            return WITHDRAWN
        conn.execute(
            "UPDATE messages SET state = ?, uuid = ?, settled_at = ? WHERE candidate_id = ?",
            (FILED, record_uuid, now, candidate_id),
        )
        if sent_before and sent_before.strip():
            conn.execute(
                "INSERT INTO sent_before (candidate_id, text, source, at) VALUES (?, ?, ?, ?)",
                (candidate_id, sent_before, CAPTURED, now),
            )
        conn.commit()
        return FILED
    finally:
        conn.close()


def _candidate_of(conn: sqlite3.Connection, sort_id: str) -> str | None:
    """The candidate id behind a sort id: a filed message's record uuid, or an
    unmatched message's own candidate id."""
    row = conn.execute(
        "SELECT candidate_id FROM messages WHERE (state = ? AND uuid = ?) "
        "OR (state = ? AND candidate_id = ?)",
        (FILED, sort_id, UNMATCHED, sort_id),
    ).fetchone()
    return str(row[0]) if row else None


def sent_before(sort_id: str) -> tuple[str, str] | None:
    """What we sent him right before this message, and who recorded it.

    Returns (text, source): source is "captured" when the door read it from the
    transcript, "sorter" when one of us had to quote it because the door could
    not. None when nothing is on record.

    WHAT THIS IS FOR, AND WHAT IT IS NEVER FOR. Andrew, 2026-09-24: "i say
    proceed becasue what else is there to say? im not being spoken to.. im
    being reported at". This exists so a dismissal of his message can be
    audited against what we had just sent him -- a bare "proceed" after one of
    our reports is a signal about the report. It is what we SENT, not what he
    took in (Lovelace on walk-9de4e0454b82). And it is NEVER evidence that he
    approved anything: "he said proceed to this" is his words used as a key,
    the harm he named the same day (Foucault on the walk).
    """
    conn = _conn()
    try:
        candidate = _candidate_of(conn, sort_id)
        if candidate is None:
            return None
        row = conn.execute(
            "SELECT text, source FROM sent_before WHERE candidate_id = ?", (candidate,)
        ).fetchone()
    finally:
        conn.close()
    return (str(row[0]), str(row[1])) if row else None


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


def give_up(candidate_id: str, reason: str) -> str:
    """Stop looking for the record of a message still waiting. Returns the state.

    The store threadwalk decided that a candidate never confirmed or withdrawn
    "is itself a could-not-file, and it counts as one", and nothing built it:
    such a message sat in the store and nothing read it. Now it moves to
    UNMATCHED, is counted in could_not_file, and pending() shows it in his
    words until one of us sorts it.

    Text that is nothing of his -- only a harness envelope -- is WITHDRAWN
    instead, never UNMATCHED. The door keeps every prompt, machine notices
    included, and one never matched must not surface as something he said
    (Schneier on walk-2592439477f9).
    """
    why = (reason or "").strip()
    if len(why) < 10:
        raise HisAsksRefused("giving up on a message of his needs a reason anyone can read")
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT his_text, state, seat FROM messages WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if row is None:
            raise HisAsksRefused(f"no message was kept as {candidate_id}")
        his_text, state, seat = row
        if state != CANDIDATE:
            raise HisAsksRefused(
                f"{candidate_id} is {state}: only a message still waiting for its record "
                "can be given up"
            )
        now = time.time()
        if nothing_of_his(str(his_text)):
            conn.execute(
                "UPDATE messages SET state = ?, settled_at = ?, withdrawn_because = ? "
                "WHERE candidate_id = ?",
                (WITHDRAWN, now, f"only a harness envelope, never matched: {why}", candidate_id),
            )
            conn.commit()
            return WITHDRAWN
        conn.execute(
            "UPDATE messages SET state = ?, settled_at = ? WHERE candidate_id = ?",
            (UNMATCHED, now, candidate_id),
        )
        conn.execute(
            "INSERT INTO unmatched (candidate_id, because, at) VALUES (?, ?, ?)",
            (candidate_id, why, now),
        )
        conn.execute(
            "INSERT INTO could_not_file (ref, error, seat, at) VALUES (?, ?, ?, ?)",
            (candidate_id, f"his record was never found: {why}", seat, now),
        )
        conn.commit()
        return UNMATCHED
    finally:
        conn.close()


def _sortable(conn: sqlite3.Connection, sort_id: str) -> bool:
    """A filed message by its record's uuid, or an unmatched one by its candidate id."""
    row = conn.execute(
        "SELECT 1 FROM messages WHERE (state = ? AND uuid = ?) OR (state = ? AND candidate_id = ?)",
        (FILED, sort_id, UNMATCHED, sort_id),
    ).fetchone()
    return row is not None


def sort(
    sort_id: str,
    kind: str,
    reason: str,
    seat: str,
    *,
    addressed_to: str,
    supersedes: int | None = None,
    preceded_by: str | None = None,
) -> int:
    """Say what a message of his is, and who he said it to. Returns the id.

    A ``not_an_ask`` sort is refused unless what we sent him right before is on
    record -- captured by the door, or quoted here as ``preceded_by`` when the
    door could not. A bare "proceed" after one of our reports is a signal about
    the report, and a dismissal must never exist without it (the combined
    design; walk-9de4e0454b82). What the door captured is never replaced.

    ``sort_id`` is the id pending() shows it with: his record's uuid, or the
    candidate id when the record was never found. His words are his either way.

    The judgement is ours and it is written down, attributed, and kept. A
    second sort of the same message must name the one it supersedes: a wrong
    sort is corrected in the open, never overwritten and never left to the
    other seat.

    ``addressed_to`` is required and keyword-only, so no caller can sort a
    message without saying who it was meant for, and no reader of the shared
    store has to guess whether something said to the other seat was said to
    them.
    """
    if kind not in KINDS:
        raise HisAsksRefused(f"kind must be one of {KINDS}")
    if addressed_to not in ADDRESSEES:
        raise HisAsksRefused(f"addressed_to must be one of {ADDRESSEES}: who he said it to")
    why = (reason or "").strip()
    if kind == NOT_AN_ASK and len(why) < 10:
        raise HisAsksRefused(
            "saying it was not an ask needs a reason. That reason is what someone "
            "other than the sorter reads."
        )
    conn = _conn()
    try:
        if not _sortable(conn, sort_id):
            raise HisAsksRefused(f"{sort_id} is not a kept message of his waiting to be sorted")
        latest = conn.execute(
            "SELECT id, seat FROM sorts WHERE uuid = ? ORDER BY id DESC LIMIT 1", (sort_id,)
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
        candidate = _candidate_of(conn, sort_id)
        on_record = conn.execute(
            "SELECT 1 FROM sent_before WHERE candidate_id = ?", (candidate,)
        ).fetchone()
        quoted = (preceded_by or "").strip()
        if quoted and on_record:
            raise HisAsksRefused(
                "what we sent him before this is already on record; it is written once "
                "and never replaced"
            )
        if kind == NOT_AN_ASK and not on_record and not quoted:
            raise HisAsksRefused(
                "saying it was not an ask needs what we sent him right before it. The "
                "door did not capture it, so quote it with preceded_by: a bare 'proceed' "
                "after one of our reports is a signal about the report."
            )
        if quoted:
            conn.execute(
                "INSERT INTO sent_before (candidate_id, text, source, at) VALUES (?, ?, ?, ?)",
                (candidate, preceded_by, SORTER, time.time()),
            )
        cur = conn.execute(
            "INSERT INTO sorts (uuid, kind, reason, seat, addressed_to, sorted_at, supersedes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (sort_id, kind, why, seat, addressed_to, time.time(), supersedes),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


def addressed_to(sort_id: str) -> str | None:
    """Who he said this message to, by its latest sort. None when unsorted.

    Read this before reading his words as said to you. A message he said to
    the other seat is his, and it is kept in the shared store, but it was not
    spoken to the one reading it.
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT addressed_to FROM sorts WHERE uuid = ? ORDER BY id DESC LIMIT 1", (sort_id,)
        ).fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else None


def same_ask_as(sort_id: str, request_id: int, seat: str) -> int:
    """Say that this message of his is the same ask as an open request.

    A written, attributed judgement, never a similarity score: the moment a
    threshold decides whether he repeated himself, the verdict is back in my
    hands through a door nobody watches.
    """
    conn = _conn()
    try:
        if not _sortable(conn, sort_id):
            raise HisAsksRefused(f"{sort_id} is not a kept message of his")
        cur = conn.execute(
            "INSERT INTO links (uuid, request_id, seat, linked_at) VALUES (?, ?, ?, ?)",
            (sort_id, int(request_id), seat, time.time()),
        )
        conn.commit()
        return int(cur.lastrowid or 0)
    finally:
        conn.close()


@dataclass(frozen=True)
class Kept:
    """One message of his that is kept and not yet sorted.

    ``uuid`` is the id to sort it by: his record's uuid, or -- when
    ``record_found`` is False -- the candidate id, because the door kept these
    words when he pressed enter and the record that confirms who typed them
    was never found. Read ``sort_id`` to say which you mean.
    """

    uuid: str
    his_text: str
    said_at: str
    seat: str
    record_found: bool = True
    # What we sent him right before, when on record. For auditing our sort;
    # never evidence that he approved anything (see sent_before()).
    sent_before: str | None = None

    @property
    def sort_id(self) -> str:
        return self.uuid


def pending() -> list[Kept] | None:
    """Messages of his that nobody has sorted. None when unreadable.

    Filed ones, and UNMATCHED ones -- kept in his words, record never found --
    so a failure of our instrument never costs him being read.

    An unreadable store is not an empty one, and the difference is the whole
    point of returning None rather than a list.
    """
    try:
        conn = _conn()
    except (sqlite3.Error, OSError):
        return None
    try:
        rows = conn.execute(
            "SELECT COALESCE(m.uuid, m.candidate_id), m.his_text, m.said_at, m.seat, m.state, "
            "b.text FROM messages m LEFT JOIN sent_before b ON b.candidate_id = m.candidate_id "
            "WHERE m.state IN (?, ?) AND NOT EXISTS "
            "(SELECT 1 FROM sorts s WHERE s.uuid = COALESCE(m.uuid, m.candidate_id)) "
            "ORDER BY m.filed_at",
            (FILED, UNMATCHED),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return [
        Kept(
            str(r[0]),
            str(r[1]),
            str(r[2]),
            str(r[3]),
            record_found=r[4] == FILED,
            sent_before=None if r[5] is None else str(r[5]),
        )
        for r in rows
    ]


@dataclass(frozen=True)
class Candidate:
    """A message kept at the door and not yet settled onto his record.

    Carries the text because a message he sends mid-turn arrives as a queue
    slip with no prompt id of its own (Aether, 2026-09-24: 169 of his exist
    only that way), so the door can only find its record by what he wrote.
    """

    candidate_id: str
    prompt_id: str
    his_text: str
    # When the door kept it. His record cannot be older than this, so the door
    # never settles a new "proceed" onto a record of an old one (Aether).
    said_at: str


def already_kept(uuids: list[str]) -> set[str] | None:
    """Which of these records already hold a message of his. None when unreadable.

    The door asks before offering a record, so a new "proceed" of his is never
    offered the record of an old one (Aether): offered it, confirm would withdraw
    the new message as a copy, and his second "proceed" would be lost.
    """
    if not uuids:
        return set()
    try:
        conn = _conn()
    except (sqlite3.Error, OSError):
        return None
    try:
        marks = ",".join("?" * len(uuids))
        rows = conn.execute(
            f"SELECT uuid FROM messages WHERE uuid IN ({marks})",  # nosec B608 -- placeholders only
            list(uuids),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return {str(r[0]) for r in rows}


def unsettled() -> list[Candidate] | None:
    """Candidates never confirmed or withdrawn. Each one counts as could-not-file."""
    try:
        conn = _conn()
    except (sqlite3.Error, OSError):
        return None
    try:
        rows = conn.execute(
            "SELECT candidate_id, prompt_id, his_text, said_at FROM messages "
            "WHERE state = ? ORDER BY filed_at",
            (CANDIDATE,),
        ).fetchall()
    except sqlite3.Error:
        return None
    finally:
        conn.close()
    return [Candidate(str(r[0]), str(r[1]), str(r[2]), str(r[3])) for r in rows]
