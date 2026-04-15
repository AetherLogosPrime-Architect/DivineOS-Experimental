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


def init_holding_table() -> None:
    """Create the holding room table."""
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
                stale         INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_holding_active
            ON holding_room(stale, promoted_to)
        """)
        conn.commit()
    finally:
        conn.close()


def hold(content: str, hint: str = "", source: str = "") -> str:
    """Put something in the holding room. No classification required.

    Args:
        content: The thing itself. A thought, observation, phrase, anything.
        hint: Optional guess about what it might become.
              e.g. "might be a lesson", "feels like an opinion", "just a vibe"
        source: Where it came from. e.g. "session", "conversation", "sleep"

    Returns:
        The item_id.
    """
    init_holding_table()
    item_id = f"hold-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO holding_room "
            "(item_id, content, hint, source, arrived_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (item_id, content, hint, source, now),
        )
        conn.commit()
        return item_id
    finally:
        conn.close()


def get_holding(include_stale: bool = False) -> list[dict[str, Any]]:
    """Get everything currently in the holding room.

    By default only shows active (non-stale, non-promoted) items.
    """
    init_holding_table()
    conn = _get_connection()
    try:
        if include_stale:
            query = "SELECT * FROM holding_room WHERE promoted_to IS NULL ORDER BY arrived_at DESC"
            rows = conn.execute(query).fetchall()
        else:
            query = (
                "SELECT * FROM holding_room "
                "WHERE promoted_to IS NULL AND stale = 0 "
                "ORDER BY arrived_at DESC"
            )
            rows = conn.execute(query).fetchall()
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
    """Convert a holding_room row to a dict."""
    return {
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
