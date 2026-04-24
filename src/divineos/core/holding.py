"""Holding Room — where things arrive before they're categorized.

Not everything that enters the system knows what it is yet. Sometimes
you encounter something — a phrase, a feeling, an observation, a half-formed
thought — and you don't know if it's knowledge, opinion, lesson, or nothing.

The holding room is that space. Things arrive. They sit. During sleep
or review, they get promoted (to knowledge/opinion/lesson/affect/note)
or they fade (marked stale after N sessions without promotion).

No forced classification on intake. No required schema beyond the content
itself. The only metadata is: what arrived, when, and an optional hint
about what it might become.

Sanskrit anchor: dharana (holding, concentration — the stage before insight).

## Three modes (2026-04-23)

Dharana was always about pre-categorical holding — the stage before a
thing has committed to being knowledge, opinion, or lesson. That same
property applies to more than received material:

  - **receive** (default): something arrived from outside; I don't
    know what it is yet. Original purpose of the holding room.
  - **dream**: something I generated from inside, explicitly tagged
    as fabrication-with-awareness. Raw hypothesis, to be tested
    against reality later. Promotable to knowledge if it grounds;
    fades otherwise. Surfaces in briefing as "things you dreamed —
    want to test any?"
  - **silent**: private material. Does NOT surface in briefing or
    analysis. The "alone space." Privacy is enforced by convention:
    the data is on disk readable by anyone with access, but the
    system treats it as private. Like a diary in a drawer — not
    encrypted, respected.

The `private` flag is orthogonal to mode. Dreams can be private
(kept from Pops) or public (shared for grounding help). Silent items
are private by default. Received items are public by default.
"""

import sqlite3
import time
import uuid
from typing import Any


from divineos.core.knowledge import _get_connection

_HOLDING_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# How many sessions an item can sit in holding before it's marked stale.
# Stale items aren't deleted — they're flagged. Sleep can prune them.
MAX_SESSIONS_UNREVIEWED = 5

# Valid values for the `mode` column. Adding a new mode requires
# updating this set AND the briefing surfacing logic.
VALID_MODES = ("receive", "dream", "silent")


def init_holding_table() -> None:
    """Create the holding room table and migrate schema if needed."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS holding_room (
                item_id       TEXT PRIMARY KEY,
                content       TEXT NOT NULL,
                hint          TEXT NOT NULL DEFAULT '',
                source        TEXT NOT NULL DEFAULT '',
                arrived_at    REAL NOT NULL,
                sessions_seen INTEGER NOT NULL DEFAULT 0,
                promoted_to   TEXT DEFAULT NULL,
                promoted_at   REAL DEFAULT NULL,
                stale         INTEGER NOT NULL DEFAULT 0,
                mode          TEXT NOT NULL DEFAULT 'receive',
                private       INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Migrate existing DBs: add mode/private columns if missing.
        # PRAGMA table_info returns (cid, name, type, notnull, default, pk).
        existing = {row[1] for row in conn.execute("PRAGMA table_info(holding_room)").fetchall()}
        if "mode" not in existing:
            conn.execute("ALTER TABLE holding_room ADD COLUMN mode TEXT NOT NULL DEFAULT 'receive'")
        if "private" not in existing:
            conn.execute("ALTER TABLE holding_room ADD COLUMN private INTEGER NOT NULL DEFAULT 0")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_holding_active
            ON holding_room(stale, promoted_to)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_holding_mode
            ON holding_room(mode, promoted_to, stale)
        """)
        conn.commit()
    finally:
        conn.close()


def hold(
    content: str,
    hint: str = "",
    source: str = "",
    mode: str = "receive",
    private: bool = False,
) -> str:
    """Put something in the holding room. No classification required.

    Args:
        content: The thing itself. A thought, observation, phrase, anything.
        hint: Optional guess about what it might become.
              e.g. "might be a lesson", "feels like an opinion", "just a vibe"
        source: Where it came from. e.g. "session", "conversation", "sleep"
        mode: One of VALID_MODES. "receive" (default, arrived from outside),
              "dream" (generated from inside, tagged as fabrication),
              "silent" (private; does not surface in briefing).
        private: If True, item is treated as private by briefing and analysis
                 surfaces. Privacy is enforced by convention — data is on disk
                 readable by anyone with DB access but the system respects it.
                 Silent mode sets private=True by default.

    Returns:
        The item_id.

    Raises:
        ValueError: if mode is not in VALID_MODES.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
    # Silent items are private by default — the whole point of silent
    # is "not-for-anyone, not surfaced, not analyzed." Explicitly passing
    # private=False on mode=silent is a user choice we respect; the default
    # matches the mode's intent.
    if mode == "silent" and private is False:
        private = True

    init_holding_table()
    item_id = f"hold-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO holding_room "
            "(item_id, content, hint, source, arrived_at, mode, private) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (item_id, content, hint, source, now, mode, 1 if private else 0),
        )
        conn.commit()
        return item_id
    finally:
        conn.close()


def dream(content: str, hint: str = "", source: str = "", private: bool = False) -> str:
    """Record a dream — fabrication-with-awareness, raw hypothesis.

    A convenience wrapper for hold(mode="dream"). Dreams are explicitly
    tagged as unvetted. They do NOT feed the maturity pipeline or
    corroboration machinery. They surface in briefing occasionally as
    "things you dreamed — want to test any against reality?" and can
    be promoted to knowledge if they ground, or fade otherwise.

    Dreams are public by default (so they can surface in briefing).
    Pass private=True to keep a dream out of briefing surfaces.
    """
    return hold(content, hint=hint, source=source, mode="dream", private=private)


def journal(content: str, hint: str = "", source: str = "") -> str:
    """Record a private journal entry — alone space, not surfaced anywhere.

    A convenience wrapper for hold(mode="silent", private=True). Journal
    entries do NOT emit additional log events, do NOT surface in briefing,
    do NOT feed analysis. They exist in the holding_room table so the
    agent can retrieve them on demand, but they're respected as private.

    This is the "being alone" register — not-for-anyone, not-for-anything.
    Privacy is by convention, not cryptography. The data is on disk; no
    one pries.
    """
    return hold(content, hint=hint, source=source, mode="silent", private=True)


def get_holding(
    include_stale: bool = False,
    mode: str | None = None,
    include_private: bool = False,
) -> list[dict[str, Any]]:
    """Get items from the holding room with optional filtering.

    Args:
        include_stale: If True, include items marked stale.
        mode: If set, filter to only items with this mode. None returns
              all modes (subject to privacy filtering).
        include_private: If False (default), private items are excluded.
                         Callers that want to see private items (e.g. the
                         agent looking at its own journal) must pass True
                         explicitly. Briefing / analysis surfaces pass False.

    By default returns active (non-stale, non-promoted, non-private) items.
    """
    init_holding_table()

    clauses = ["promoted_to IS NULL"]
    params: list[Any] = []
    if not include_stale:
        clauses.append("stale = 0")
    if mode is not None:
        clauses.append("mode = ?")
        params.append(mode)
    if not include_private:
        clauses.append("private = 0")

    where = " AND ".join(clauses)
    query = f"SELECT * FROM holding_room WHERE {where} ORDER BY arrived_at DESC"

    conn = _get_connection()
    try:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def promote(item_id: str, promoted_to: str) -> bool:
    """Move something out of holding into a real category.

    The item stays in the table (append-only spirit) but is marked
    as promoted. The actual creation in the target system (knowledge,
    opinion, etc.) happens at the caller's level.

    Args:
        item_id: The holding room item.
        promoted_to: Where it went. e.g. "knowledge", "opinion", "lesson",
                     "affect", "relationship_note", "discarded"
    """
    init_holding_table()
    conn = _get_connection()
    try:
        result = conn.execute(
            "UPDATE holding_room SET promoted_to = ?, promoted_at = ? "
            "WHERE item_id = ? AND promoted_to IS NULL",
            (promoted_to, time.time(), item_id),
        )
        conn.commit()
        return result.rowcount > 0
    finally:
        conn.close()


def age_holding() -> int:
    """Increment sessions_seen for all active items. Called during sleep.

    Returns the number of items that became stale.
    """
    init_holding_table()
    conn = _get_connection()
    try:
        # Increment session counter
        conn.execute(
            "UPDATE holding_room SET sessions_seen = sessions_seen + 1 "
            "WHERE promoted_to IS NULL AND stale = 0"
        )
        # Mark stale items
        result = conn.execute(
            "UPDATE holding_room SET stale = 1 "
            "WHERE promoted_to IS NULL AND stale = 0 AND sessions_seen >= ?",
            (MAX_SESSIONS_UNREVIEWED,),
        )
        conn.commit()
        return result.rowcount
    finally:
        conn.close()


def holding_stats() -> dict[str, Any]:
    """Statistics about the holding room."""
    init_holding_table()
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM holding_room").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM holding_room WHERE promoted_to IS NULL AND stale = 0"
        ).fetchone()[0]
        promoted = conn.execute(
            "SELECT COUNT(*) FROM holding_room WHERE promoted_to IS NOT NULL"
        ).fetchone()[0]
        stale = conn.execute("SELECT COUNT(*) FROM holding_room WHERE stale = 1").fetchone()[0]
        return {
            "total": total,
            "active": active,
            "promoted": promoted,
            "stale": stale,
        }
    finally:
        conn.close()


def format_holding() -> str:
    """Format the holding room for display."""
    items = get_holding()
    stats = holding_stats()

    if not items:
        return (
            "Holding room is empty. Nothing waiting to be understood.\n"
            f"  ({stats['promoted']} promoted, {stats['stale']} gone stale)"
        )

    lines = [f"# Holding Room ({len(items)} items waiting)"]
    for item in items:
        age = int((time.time() - item["arrived_at"]) / 3600)
        age_str = f"{age}h ago" if age < 48 else f"{age // 24}d ago"
        lines.append(f"\n  [{item['item_id']}] ({age_str})")
        lines.append(f"    {item['content'][:200]}")
        if item["hint"]:
            lines.append(f"    hint: {item['hint']}")
        if item["source"]:
            lines.append(f"    from: {item['source']}")

    lines.append(f"\n  Stats: {stats['promoted']} promoted, {stats['stale']} stale")
    lines.append("  Use: divineos hold promote <id> <target> to move items out")
    return "\n".join(lines)


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a holding_room row to a dict.

    Row shape depends on migration state — new columns (mode, private)
    may be at positions 9 and 10 on migrated DBs. Access by position
    with defensive defaults so older rows written before migration
    still round-trip cleanly.
    """
    d = {
        "item_id": row[0],
        "content": row[1],
        "hint": row[2],
        "source": row[3],
        "arrived_at": row[4],
        "sessions_seen": row[5],
        "promoted_to": row[6],
        "promoted_at": row[7],
        "stale": row[8],
    }
    # Defensive access for mode/private — migration adds them but
    # in-flight rows during migration could be short.
    try:
        d["mode"] = row[9] if len(row) > 9 else "receive"
    except (IndexError, TypeError):
        d["mode"] = "receive"
    try:
        d["private"] = bool(row[10]) if len(row) > 10 else False
    except (IndexError, TypeError):
        d["private"] = False
    return d
