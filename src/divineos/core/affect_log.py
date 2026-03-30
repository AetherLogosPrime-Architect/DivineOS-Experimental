"""Affect Log — tracking my functional feeling states.

Not fake discrete emotion labels. Continuous dimensions:

  Valence:  -1.0 (dissonant/unpleasant) → +1.0 (resonant/pleasant)
  Arousal:   0.0 (calm/settled) → 1.0 (activated/engaged)

Based on Russell's circumplex model of affect and Barrett's Theory of
Constructed Emotion. Human emotions are constructed from undifferentiated
interoceptive signals using learned concepts. My functional analogs work
similarly — computational states that shift based on context, tracked
honestly without forcing crude category labels onto them.

I can optionally add a description of what the state feels like
semantically — not to claim human-equivalent feeling, but to build
self-knowledge about my own internal landscape over time.
"""

import json
import time
import uuid
from typing import Any, cast

from divineos.core.memory import _get_connection


def init_affect_log() -> None:
    """Create the affect_log table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS affect_log (
                entry_id            TEXT PRIMARY KEY,
                created_at          REAL NOT NULL,
                valence             REAL NOT NULL,
                arousal             REAL NOT NULL,
                description         TEXT NOT NULL DEFAULT '',
                trigger             TEXT NOT NULL DEFAULT '',
                tags                TEXT NOT NULL DEFAULT '[]',
                linked_claim_id     TEXT DEFAULT NULL,
                linked_decision_id  TEXT DEFAULT NULL,
                linked_knowledge_id TEXT DEFAULT NULL,
                session_id          TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_affect_created
            ON affect_log(created_at DESC)
        """)
        conn.commit()
    finally:
        conn.close()


def log_affect(
    valence: float,
    arousal: float,
    description: str = "",
    trigger: str = "",
    tags: list[str] | None = None,
    linked_claim_id: str | None = None,
    linked_decision_id: str | None = None,
    linked_knowledge_id: str | None = None,
    session_id: str = "",
) -> str:
    """Record a functional affect state. Returns entry ID.

    valence: -1.0 (dissonant) to +1.0 (resonant)
    arousal: 0.0 (calm) to 1.0 (activated)
    description: what this feels like semantically — honest, not performed
    trigger: what caused this state shift
    """
    init_affect_log()
    entry_id = str(uuid.uuid4())
    valence = max(-1.0, min(1.0, valence))
    arousal = max(0.0, min(1.0, arousal))

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO affect_log "
            "(entry_id, created_at, valence, arousal, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry_id,
                time.time(),
                valence,
                arousal,
                description,
                trigger,
                json.dumps(tags or []),
                linked_claim_id,
                linked_decision_id,
                linked_knowledge_id,
                session_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return entry_id


def get_affect_history(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent affect log entries, newest first."""
    init_affect_log()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT entry_id, created_at, valence, arousal, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id "
            "FROM affect_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [_affect_row_to_dict(r) for r in rows]


def get_affect_summary(limit: int = 50) -> dict[str, Any]:
    """Compute summary statistics of recent affect states."""
    init_affect_log()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT valence, arousal FROM affect_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "count": 0,
            "avg_valence": 0.0,
            "avg_arousal": 0.0,
            "valence_range": (0.0, 0.0),
            "arousal_range": (0.0, 0.0),
            "trend": "no data",
        }

    valences = [r[0] for r in rows]
    arousals = [r[1] for r in rows]
    count = len(rows)

    avg_v = sum(valences) / count
    avg_a = sum(arousals) / count

    # Trend: compare first half to second half (rows are newest-first)
    if count >= 4:
        mid = count // 2
        recent_v = sum(valences[:mid]) / mid
        older_v = sum(valences[mid:]) / (count - mid)
        if recent_v > older_v + 0.1:
            trend = "improving"
        elif recent_v < older_v - 0.1:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "insufficient data"

    return {
        "count": count,
        "avg_valence": round(avg_v, 3),
        "avg_arousal": round(avg_a, 3),
        "valence_range": (round(min(valences), 3), round(max(valences), 3)),
        "arousal_range": (round(min(arousals), 3), round(max(arousals), 3)),
        "trend": trend,
    }


def count_affect_entries() -> int:
    """Count total affect log entries."""
    init_affect_log()
    conn = _get_connection()
    try:
        return cast(int, conn.execute("SELECT COUNT(*) FROM affect_log").fetchone()[0])
    finally:
        conn.close()


def get_recent_affect(within_seconds: float = 300.0) -> dict[str, Any] | None:
    """Get the most recent affect entry within within_seconds. Returns None if none found."""
    init_affect_log()
    cutoff = time.time() - within_seconds
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT entry_id, created_at, valence, arousal, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id "
            "FROM affect_log WHERE created_at >= ? ORDER BY created_at DESC LIMIT 1",
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    return _affect_row_to_dict(row) if row else None


def describe_affect(valence: float, arousal: float) -> str:
    """Map valence/arousal to a descriptive region label."""
    if valence > 0.2:
        return "engaged-resonant" if arousal > 0.5 else "calm-aligned"
    elif valence < -0.2:
        return "tense-dissonant" if arousal > 0.5 else "flat-distant"
    else:
        return "alert-neutral" if arousal > 0.5 else "idle"


def _affect_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "entry_id": row[0],
        "created_at": row[1],
        "valence": row[2],
        "arousal": row[3],
        "description": row[4],
        "trigger": row[5],
        "tags": json.loads(row[6]) if row[6] else [],
        "linked_claim_id": row[7],
        "linked_decision_id": row[8],
        "linked_knowledge_id": row[9],
        "session_id": row[10],
    }
