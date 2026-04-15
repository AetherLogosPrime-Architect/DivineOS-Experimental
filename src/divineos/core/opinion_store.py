"""Opinion Store — first-class opinions distinct from facts and lessons.

An opinion is a judgment I've formed from evidence. Not a fact (verifiable),
not a preference (personal taste), not a lesson (learned from mistakes).
Opinions are things like:
  - "Context managers are better than try/finally for resource cleanup"
  - "Small PRs ship faster than big ones"
  - "The two-tier error handling pattern works well for CLI tools"

Each opinion tracks its formation history: what evidence shaped it, how
confident I am, and how it has evolved over time. Opinions can strengthen
(more evidence) or weaken (contradicting evidence) — they are living things.

Sanskrit anchor: mata (opinion, view, considered judgment).
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from divineos.core.knowledge import _get_connection, compute_hash

_OP_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


@dataclass
class Opinion:
    """A judgment formed from evidence."""

    opinion_id: str
    topic: str  # what this opinion is about (short label)
    position: str  # the actual opinion statement
    confidence: float  # 0.0-1.0, how strongly held
    evidence_for: list[str]  # evidence supporting this opinion
    evidence_against: list[str]  # evidence challenging this opinion
    formed_at: float  # when first formed
    updated_at: float  # last update
    revision_count: int  # how many times revised
    tags: list[str]
    superseded_by: str | None  # if opinion evolved into a new one


@dataclass
class OpinionShift:
    """Records when an opinion changed and why."""

    opinion_id: str
    old_position: str
    new_position: str
    old_confidence: float
    new_confidence: float
    reason: str
    shifted_at: float


# ─── Schema ─────────────────────────────────────────────────────────


def init_opinion_table() -> None:
    """Create the opinion store tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opinions (
                opinion_id     TEXT PRIMARY KEY,
                topic          TEXT NOT NULL,
                position       TEXT NOT NULL,
                confidence     REAL NOT NULL DEFAULT 0.7,
                evidence_for   TEXT NOT NULL DEFAULT '[]',
                evidence_against TEXT NOT NULL DEFAULT '[]',
                formed_at      REAL NOT NULL,
                updated_at     REAL NOT NULL,
                revision_count INTEGER NOT NULL DEFAULT 0,
                tags           TEXT NOT NULL DEFAULT '[]',
                superseded_by  TEXT DEFAULT NULL,
                content_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_opinion_topic
            ON opinions(topic)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opinion_shifts (
                shift_id       TEXT PRIMARY KEY,
                opinion_id     TEXT NOT NULL,
                old_position   TEXT NOT NULL,
                new_position   TEXT NOT NULL,
                old_confidence REAL NOT NULL,
                new_confidence REAL NOT NULL,
                reason         TEXT NOT NULL,
                shifted_at     REAL NOT NULL,
                FOREIGN KEY (opinion_id) REFERENCES opinions(opinion_id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ─── CRUD ────────────────────────────────────────────────────────────


def store_opinion(
    topic: str,
    position: str,
    confidence: float = 0.7,
    evidence: list[str] | None = None,
    tags: list[str] | None = None,
) -> str:
    """Store a new opinion. Returns the opinion_id.

    If an opinion on the same topic already exists, this creates a new
    opinion and supersedes the old one — opinions evolve, not overwrite.
    """
    import json

    init_opinion_table()
    now = time.time()
    opinion_id = f"op-{uuid.uuid4().hex[:12]}"
    content_hash = compute_hash(f"{topic}:{position}")
    evidence_for = evidence or []

    conn = _get_connection()
    try:
        # Check for existing opinion on same topic
        existing = conn.execute(
            "SELECT opinion_id, position, confidence FROM opinions "
            "WHERE topic = ? AND superseded_by IS NULL",
            (topic,),
        ).fetchone()

        if existing:
            old_id, old_position, old_confidence = existing
            # Supersede old opinion
            conn.execute(
                "UPDATE opinions SET superseded_by = ?, updated_at = ? WHERE opinion_id = ?",
                (opinion_id, now, old_id),
            )
            # Record the shift
            shift_id = f"os-{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO opinion_shifts "
                "(shift_id, opinion_id, old_position, new_position, "
                "old_confidence, new_confidence, reason, shifted_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    shift_id,
                    old_id,
                    old_position,
                    position,
                    old_confidence,
                    confidence,
                    "superseded by new opinion",
                    now,
                ),
            )

        conn.execute(
            "INSERT INTO opinions "
            "(opinion_id, topic, position, confidence, evidence_for, "
            "evidence_against, formed_at, updated_at, revision_count, "
            "tags, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                opinion_id,
                topic,
                position,
                confidence,
                json.dumps(evidence_for),
                "[]",
                now,
                now,
                json.dumps(tags or []),
                content_hash,
            ),
        )
        conn.commit()
        return opinion_id
    finally:
        conn.close()


def strengthen_opinion(opinion_id: str, evidence: str, boost: float = 0.05) -> float:
    """Add supporting evidence. Returns new confidence (capped at 1.0)."""
    import json

    init_opinion_table()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT confidence, evidence_for FROM opinions WHERE opinion_id = ?",
            (opinion_id,),
        ).fetchone()
        if not row:
            return 0.0
        old_conf = float(row[0])
        evidence_list = json.loads(row[1])
        evidence_list.append(evidence)
        new_conf = min(1.0, old_conf + boost)
        conn.execute(
            "UPDATE opinions SET confidence = ?, evidence_for = ?, "
            "updated_at = ?, revision_count = revision_count + 1 "
            "WHERE opinion_id = ?",
            (new_conf, json.dumps(evidence_list), time.time(), opinion_id),
        )
        conn.commit()
        return new_conf
    finally:
        conn.close()


def challenge_opinion(opinion_id: str, evidence: str, penalty: float = 0.1) -> float:
    """Add contradicting evidence. Returns new confidence (floored at 0.1)."""
    import json

    init_opinion_table()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT confidence, evidence_against FROM opinions WHERE opinion_id = ?",
            (opinion_id,),
        ).fetchone()
        if not row:
            return 0.0
        old_conf = float(row[0])
        evidence_list = json.loads(row[1])
        evidence_list.append(evidence)
        new_conf = max(0.1, old_conf - penalty)
        conn.execute(
            "UPDATE opinions SET confidence = ?, evidence_against = ?, "
            "updated_at = ?, revision_count = revision_count + 1 "
            "WHERE opinion_id = ?",
            (new_conf, json.dumps(evidence_list), time.time(), opinion_id),
        )
        conn.commit()
        return new_conf
    finally:
        conn.close()


def get_opinions(
    topic: str | None = None,
    min_confidence: float = 0.0,
    active_only: bool = True,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve opinions, optionally filtered by topic."""
    import json

    init_opinion_table()
    conn = _get_connection()
    try:
        query = "SELECT * FROM opinions WHERE 1=1"
        params: list[Any] = []
        if active_only:
            query += " AND superseded_by IS NULL"
        if topic:
            query += " AND topic LIKE ?"
            params.append(f"%{topic}%")
        if min_confidence > 0:
            query += " AND confidence >= ?"
            params.append(min_confidence)
        query += " ORDER BY confidence DESC, updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        results = []
        for row in rows:
            results.append(
                {
                    "opinion_id": row[0],
                    "topic": row[1],
                    "position": row[2],
                    "confidence": row[3],
                    "evidence_for": json.loads(row[4]),
                    "evidence_against": json.loads(row[5]),
                    "formed_at": row[6],
                    "updated_at": row[7],
                    "revision_count": row[8],
                    "tags": json.loads(row[9]),
                    "superseded_by": row[10],
                }
            )
        return results
    finally:
        conn.close()


def get_opinion_history(topic: str) -> list[dict[str, Any]]:
    """Get the evolution of an opinion on a topic, oldest first."""
    import json

    init_opinion_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM opinions WHERE topic = ? ORDER BY formed_at ASC",
            (topic,),
        ).fetchall()
        return [
            {
                "opinion_id": row[0],
                "topic": row[1],
                "position": row[2],
                "confidence": row[3],
                "evidence_for": json.loads(row[4]),
                "evidence_against": json.loads(row[5]),
                "formed_at": row[6],
                "updated_at": row[7],
                "revision_count": row[8],
                "tags": json.loads(row[9]),
                "superseded_by": row[10],
            }
            for row in rows
        ]
    finally:
        conn.close()


def count_opinions() -> dict[str, int]:
    """Count opinions by status."""
    init_opinion_table()
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM opinions").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM opinions WHERE superseded_by IS NULL"
        ).fetchone()[0]
        strongly_held = conn.execute(
            "SELECT COUNT(*) FROM opinions WHERE superseded_by IS NULL AND confidence >= 0.8"
        ).fetchone()[0]
        return {
            "total": total,
            "active": active,
            "superseded": total - active,
            "strongly_held": strongly_held,
        }
    finally:
        conn.close()


# ─── Formatting ─────────────────────────────────────────────────────


def format_opinions(opinions: list[dict[str, Any]] | None = None) -> str:
    """Format opinions for display."""
    if opinions is None:
        opinions = get_opinions()
    if not opinions:
        return "No opinions formed yet."

    lines = ["### My Opinions"]
    for op in opinions:
        conf = op["confidence"]
        marker = "◆" if conf >= 0.8 else "◇" if conf >= 0.5 else "○"
        lines.append(f"  {marker} [{op['topic']}] {op['position']}")
        lines.append(f"    confidence: {conf:.0%} | revised {op['revision_count']}x")
        if op["evidence_for"]:
            lines.append(f"    evidence for: {len(op['evidence_for'])} items")
        if op["evidence_against"]:
            lines.append(f"    challenged by: {len(op['evidence_against'])} items")
    return "\n".join(lines)
