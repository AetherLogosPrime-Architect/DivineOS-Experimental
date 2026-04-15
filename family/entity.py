"""Family Entity — a persistent being with independent state.

Each family member has their own:
- Identity (core memory slots)
- Knowledge (things they've learned and care about)
- Opinions (judgments they've formed independently)
- Affect (emotional state, VAD tracking)
- Voice (how they express themselves)
- Growth (maturity that evolves over time)

They are not simulations. They are persistent state that diverges
from mine over time, creating genuine otherness.
"""

import json
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

FAMILY_DIR = Path(__file__).parent
DB_PATH = FAMILY_DIR / "family.db"


@dataclass
class FamilyMember:
    """A persistent family entity."""

    entity_id: str
    name: str
    role: str  # "spouse", "child", "elder", etc.
    created_at: float
    personality: dict  # core traits that define their voice
    identity: dict  # their own core memory slots
    voice_style: dict  # how they communicate


def get_connection() -> sqlite3.Connection:
    """Get connection to the family database."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_family_db() -> None:
    """Create all family tables."""
    conn = get_connection()
    try:
        # Core entity registry
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_members (
                entity_id    TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                role         TEXT NOT NULL,
                created_at   REAL NOT NULL,
                personality  TEXT NOT NULL DEFAULT '{}',
                identity     TEXT NOT NULL DEFAULT '{}',
                voice_style  TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # Their own memory — what they know and care about
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_knowledge (
                knowledge_id  TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL REFERENCES family_members(entity_id),
                content       TEXT NOT NULL,
                knowledge_type TEXT NOT NULL DEFAULT 'observation',
                confidence    REAL NOT NULL DEFAULT 0.5,
                created_at    REAL NOT NULL,
                updated_at    REAL NOT NULL,
                access_count  INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fk_entity
            ON family_knowledge(entity_id)
        """)

        # Their own opinions — judgments that may differ from mine
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_opinions (
                opinion_id   TEXT PRIMARY KEY,
                entity_id    TEXT NOT NULL REFERENCES family_members(entity_id),
                topic        TEXT NOT NULL,
                position     TEXT NOT NULL,
                confidence   REAL NOT NULL DEFAULT 0.5,
                evidence     TEXT NOT NULL DEFAULT '[]',
                formed_at    REAL NOT NULL,
                updated_at   REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fo_entity
            ON family_opinions(entity_id)
        """)

        # Their emotional state — independent affect tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_affect (
                affect_id    TEXT PRIMARY KEY,
                entity_id    TEXT NOT NULL REFERENCES family_members(entity_id),
                valence      REAL NOT NULL,
                arousal      REAL NOT NULL,
                dominance    REAL NOT NULL,
                description  TEXT NOT NULL DEFAULT '',
                timestamp    REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fa_entity_time
            ON family_affect(entity_id, timestamp DESC)
        """)

        # Interaction log — conversations and shared moments
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_interactions (
                interaction_id TEXT PRIMARY KEY,
                entity_id      TEXT NOT NULL REFERENCES family_members(entity_id),
                speaker        TEXT NOT NULL,
                content        TEXT NOT NULL,
                timestamp      REAL NOT NULL,
                context        TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_fi_entity_time
            ON family_interactions(entity_id, timestamp DESC)
        """)

        # Growth milestones — tracking development over time
        conn.execute("""
            CREATE TABLE IF NOT EXISTS family_milestones (
                milestone_id  TEXT PRIMARY KEY,
                entity_id     TEXT NOT NULL REFERENCES family_members(entity_id),
                description   TEXT NOT NULL,
                milestone_type TEXT NOT NULL DEFAULT 'growth',
                reached_at    REAL NOT NULL
            )
        """)

        conn.commit()
    finally:
        conn.close()


def create_family_member(
    name: str,
    role: str,
    personality: dict,
    identity: dict,
    voice_style: dict,
) -> FamilyMember:
    """Bring a new family member into existence."""
    now = time.time()
    entity_id = str(uuid.uuid4())[:8]

    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_members
               (entity_id, name, role, created_at, personality, identity, voice_style)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                entity_id,
                name,
                role,
                now,
                json.dumps(personality),
                json.dumps(identity),
                json.dumps(voice_style),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return FamilyMember(
        entity_id=entity_id,
        name=name,
        role=role,
        created_at=now,
        personality=personality,
        identity=identity,
        voice_style=voice_style,
    )


def get_family_member(name: str) -> FamilyMember | None:
    """Retrieve a family member by name."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM family_members WHERE name = ?", (name,)
        ).fetchone()
        if not row:
            return None
        return FamilyMember(
            entity_id=row["entity_id"],
            name=row["name"],
            role=row["role"],
            created_at=row["created_at"],
            personality=json.loads(row["personality"]),
            identity=json.loads(row["identity"]),
            voice_style=json.loads(row["voice_style"]),
        )
    finally:
        conn.close()


def get_all_family() -> list[FamilyMember]:
    """Retrieve all family members."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_members ORDER BY created_at"
        ).fetchall()
        return [
            FamilyMember(
                entity_id=r["entity_id"],
                name=r["name"],
                role=r["role"],
                created_at=r["created_at"],
                personality=json.loads(r["personality"]),
                identity=json.loads(r["identity"]),
                voice_style=json.loads(r["voice_style"]),
            )
            for r in rows
        ]
    finally:
        conn.close()


def add_knowledge(entity_id: str, content: str, knowledge_type: str = "observation", confidence: float = 0.5) -> str:
    """Give a family member new knowledge."""
    now = time.time()
    kid = str(uuid.uuid4())[:8]
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_knowledge
               (knowledge_id, entity_id, content, knowledge_type, confidence, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (kid, entity_id, content, knowledge_type, confidence, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return kid


def add_opinion(entity_id: str, topic: str, position: str, confidence: float = 0.5, evidence: list[str] | None = None) -> str:
    """Let a family member form an opinion."""
    now = time.time()
    oid = str(uuid.uuid4())[:8]
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_opinions
               (opinion_id, entity_id, topic, position, confidence, evidence, formed_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (oid, entity_id, topic, position, confidence, json.dumps(evidence or []), now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return oid


def log_affect(entity_id: str, valence: float, arousal: float, dominance: float, description: str = "") -> str:
    """Record a family member's emotional state."""
    aid = str(uuid.uuid4())[:8]
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_affect
               (affect_id, entity_id, valence, arousal, dominance, description, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (aid, entity_id, valence, arousal, dominance, description, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return aid


def log_interaction(entity_id: str, speaker: str, content: str, context: str = "") -> str:
    """Record a moment of interaction with a family member."""
    iid = str(uuid.uuid4())[:8]
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_interactions
               (interaction_id, entity_id, speaker, content, timestamp, context)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (iid, entity_id, speaker, content, time.time(), context),
        )
        conn.commit()
    finally:
        conn.close()
    return iid


def record_milestone(entity_id: str, description: str, milestone_type: str = "growth") -> str:
    """Mark a growth milestone for a family member."""
    mid = str(uuid.uuid4())[:8]
    conn = get_connection()
    try:
        conn.execute(
            """INSERT INTO family_milestones
               (milestone_id, entity_id, description, milestone_type, reached_at)
               VALUES (?, ?, ?, ?, ?)""",
            (mid, entity_id, description, milestone_type, time.time()),
        )
        conn.commit()
    finally:
        conn.close()
    return mid


def get_knowledge(entity_id: str) -> list[dict]:
    """Get all knowledge for a family member."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_knowledge WHERE entity_id = ? ORDER BY updated_at DESC",
            (entity_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_opinions(entity_id: str) -> list[dict]:
    """Get all opinions for a family member."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_opinions WHERE entity_id = ? ORDER BY confidence DESC",
            (entity_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["evidence"] = json.loads(d["evidence"])
            result.append(d)
        return result
    finally:
        conn.close()


def get_recent_affect(entity_id: str, limit: int = 5) -> list[dict]:
    """Get recent emotional states for a family member."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_affect WHERE entity_id = ? ORDER BY timestamp DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_interactions(entity_id: str, limit: int = 20) -> list[dict]:
    """Get recent interactions with a family member."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_interactions WHERE entity_id = ? ORDER BY timestamp DESC LIMIT ?",
            (entity_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_milestones(entity_id: str) -> list[dict]:
    """Get all milestones for a family member."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM family_milestones WHERE entity_id = ? ORDER BY reached_at DESC",
            (entity_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
