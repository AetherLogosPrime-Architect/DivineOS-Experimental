"""Temporal Dimension — knowledge knows when it was true.

Facts aren't eternal. "The API uses v2" replaced "the API uses v1" at a
specific point in time. Without temporal bounds, superseded knowledge
is just marked "old" — we lose the history of when things changed.

With temporal bounds:
  - valid_from: when this knowledge became true
  - valid_until: when it stopped being true (NULL = still valid)

This enables:
  - "What was true at time X?"
  - "What changed since last session?"
  - Time-aware retrieval that respects knowledge validity windows
"""

import time
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _get_connection,
    _row_to_dict,
)


# ─── Schema Migration ───────────────────────────────────────────────


def init_temporal_columns() -> None:
    """Add valid_from and valid_until columns to the knowledge table.

    Safe to call multiple times — uses the same ALTER TABLE pattern
    as other schema migrations in _base.py.
    """
    import sqlite3

    conn = _get_connection()
    try:
        for col, col_type, default in [
            ("valid_from", "REAL", "NULL"),
            ("valid_until", "REAL", "NULL"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE knowledge ADD COLUMN {col} {col_type} DEFAULT {default}",
                )
            except sqlite3.OperationalError as e:
                logger.debug("Column %s already exists in knowledge table: %s", col, e)
        conn.commit()
    finally:
        conn.close()


# ─── Temporal Operations ────────────────────────────────────────────


def set_validity(
    knowledge_id: str,
    valid_from: float | None = None,
    valid_until: float | None = None,
) -> bool:
    """Set temporal bounds on a knowledge entry. Returns True if found."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return False

        conn.execute(
            "UPDATE knowledge SET valid_from = ?, valid_until = ? WHERE knowledge_id = ?",
            (valid_from, valid_until, knowledge_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def expire_knowledge(knowledge_id: str) -> bool:
    """Mark knowledge as no longer valid (sets valid_until to now).

    This is different from supersession — the knowledge isn't replaced,
    it's just no longer current.
    """
    return set_validity(knowledge_id, valid_until=time.time())


def stamp_valid_from(knowledge_id: str) -> bool:
    """Set valid_from to now, if not already set."""
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT valid_from FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return False
        # Only stamp if not already set
        if row[0] is not None:
            return True
        conn.execute(
            "UPDATE knowledge SET valid_from = ? WHERE knowledge_id = ?",
            (time.time(), knowledge_id),
        )
        conn.commit()
        return True
    except Exception:
        # valid_from column might not exist yet
        return False
    finally:
        conn.close()


# ─── Temporal Queries ───────────────────────────────────────────────


def get_valid_at(timestamp: float, limit: int = 50) -> list[dict[str, Any]]:
    """Get knowledge that was valid at a specific point in time.

    An entry is valid at time T if:
      - valid_from <= T (or valid_from is NULL, meaning "always")
      - valid_until > T (or valid_until is NULL, meaning "still valid")
      - Not superseded
    """
    conn = _get_connection()
    try:
        query = f"""
            SELECT {_KNOWLEDGE_COLS} FROM knowledge
            WHERE superseded_by IS NULL
              AND (valid_from IS NULL OR valid_from <= ?)
              AND (valid_until IS NULL OR valid_until > ?)
            ORDER BY updated_at DESC
            LIMIT ?
        """
        rows = conn.execute(query, (timestamp, timestamp, limit)).fetchall()
        return [_row_to_dict(row) for row in rows]
    except Exception as e:
        # Columns might not exist yet
        logger.debug("Temporal query failed (columns may not exist): %s", e)
        return []
    finally:
        conn.close()


def get_changes_since(
    since: float,
    limit: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    """Get knowledge changes since a given timestamp.

    Returns:
      - "new": entries created after `since`
      - "expired": entries whose valid_until was set after `since`
      - "superseded": entries superseded after `since`
      - "updated": entries with updated_at after `since` (confidence changes, etc.)
    """
    conn = _get_connection()
    try:
        result: dict[str, list[dict[str, Any]]] = {
            "new": [],
            "expired": [],
            "superseded": [],
            "updated": [],
        }

        # New entries
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE created_at > ? AND superseded_by IS NULL ORDER BY created_at DESC LIMIT ?",
            (since, limit),
        ).fetchall()
        result["new"] = [_row_to_dict(r) for r in rows]

        # Superseded entries (superseded_by was set after `since`)
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NOT NULL AND updated_at > ? ORDER BY updated_at DESC LIMIT ?",
            (since, limit),
        ).fetchall()
        result["superseded"] = [_row_to_dict(r) for r in rows]

        # Try temporal columns (may not exist)
        try:
            rows = conn.execute(
                f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE valid_until IS NOT NULL AND valid_until > ? AND superseded_by IS NULL ORDER BY valid_until DESC LIMIT ?",
                (since, limit),
            ).fetchall()
            result["expired"] = [_row_to_dict(r) for r in rows]
        except Exception:
            pass

        # Updated entries (confidence/maturity changes, not new)
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE updated_at > ? AND created_at <= ? AND superseded_by IS NULL ORDER BY updated_at DESC LIMIT ?",
            (since, since, limit),
        ).fetchall()
        result["updated"] = [_row_to_dict(r) for r in rows]

        return result
    finally:
        conn.close()


def format_changes_summary(changes: dict[str, list[dict[str, Any]]]) -> str:
    """Format changes into a readable summary for briefing or CLI."""
    lines: list[str] = []

    new = changes.get("new", [])
    if new:
        lines.append(f"  + {len(new)} new entries:")
        for entry in new[:5]:
            ktype = entry.get("knowledge_type", "?")
            content = entry.get("content", "")[:80]
            lines.append(f"    [{ktype}] {content}")
        if len(new) > 5:
            lines.append(f"    ... and {len(new) - 5} more")

    superseded = changes.get("superseded", [])
    if superseded:
        lines.append(f"  ~ {len(superseded)} superseded:")
        for entry in superseded[:3]:
            content = entry.get("content", "")[:80]
            lines.append(f"    [-] {content}")

    expired = changes.get("expired", [])
    if expired:
        lines.append(f"  x {len(expired)} expired:")
        for entry in expired[:3]:
            content = entry.get("content", "")[:80]
            lines.append(f"    [x] {content}")

    updated = changes.get("updated", [])
    if updated:
        lines.append(f"  * {len(updated)} updated (confidence/maturity changes)")

    if not lines:
        lines.append("  No changes.")

    return "\n".join(lines)
