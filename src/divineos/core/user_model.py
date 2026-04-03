"""User Model — structured tracking of user preferences and skill level.

Instead of an unstructured "user_identity" core memory slot, this module
maintains a structured model of who I'm working with: their technical
skill level, communication preferences, demonstrated patterns, and
interaction history.

The model is evidence-based — skill level is inferred from what the user
does (uses git fluently, writes complex regex, asks about basics), not
from what they say about themselves.

Sanskrit anchor: paricaya (acquaintance, familiarity through experience).
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import _get_connection

_UM_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Skill levels inferred from behavior
SKILL_LEVELS = ("beginner", "intermediate", "advanced", "expert")

# Communication density preferences
DENSITY_LEVELS = ("verbose", "normal", "concise", "terse")


@dataclass
class UserPreferences:
    """Learned preferences about how the user likes to work."""

    verbosity: str = "normal"  # verbose/normal/concise/terse
    jargon_tolerance: float = 0.5  # 0.0 = plain english, 1.0 = full technical
    explanation_depth: str = "normal"  # shallow/normal/deep
    prefers_examples: bool = True
    prefers_rationale: bool = True  # wants to know WHY, not just WHAT
    commit_style: str = "ask_first"  # ask_first / auto / manual


@dataclass
class UserModel:
    """Structured model of a user built from evidence."""

    user_id: str
    name: str
    skill_level: str  # beginner/intermediate/advanced/expert
    skill_confidence: float  # how confident we are in the skill assessment
    preferences: UserPreferences
    skill_signals: list[str]  # evidence that informed skill level
    interaction_count: int  # total interactions observed
    first_seen: float
    last_seen: float
    tags: list[str]


# ─── Schema ─────────────────────────────────────────────────────────


def init_user_model_table() -> None:
    """Create user model tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_models (
                user_id           TEXT PRIMARY KEY,
                name              TEXT NOT NULL,
                skill_level       TEXT NOT NULL DEFAULT 'intermediate',
                skill_confidence  REAL NOT NULL DEFAULT 0.3,
                preferences       TEXT NOT NULL DEFAULT '{}',
                skill_signals     TEXT NOT NULL DEFAULT '[]',
                interaction_count INTEGER NOT NULL DEFAULT 0,
                first_seen        REAL NOT NULL,
                last_seen         REAL NOT NULL,
                tags              TEXT NOT NULL DEFAULT '[]'
            )
        """)
        # Signals table — individual observations about user behavior
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_signals (
                signal_id    TEXT PRIMARY KEY,
                user_id      TEXT NOT NULL,
                signal_type  TEXT NOT NULL,
                content      TEXT NOT NULL,
                observed_at  REAL NOT NULL,
                session_id   TEXT DEFAULT NULL,
                FOREIGN KEY (user_id) REFERENCES user_models(user_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_signals_user
            ON user_signals(user_id)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Signal Types ────────────────────────────────────────────────────

# What we observe about users
SIGNAL_TYPES = {
    "skill_high",  # evidence of advanced skill
    "skill_low",  # evidence of beginner behavior
    "prefers_brief",  # asked for less detail
    "prefers_detail",  # asked for more detail
    "prefers_examples",  # responded well to examples
    "prefers_rationale",  # wants to know why
    "jargon_used",  # user used technical jargon fluently
    "jargon_confused",  # user asked what a term means
    "correction_given",  # user corrected the agent
    "encouragement_given",  # user praised the agent
    "frustration_shown",  # user showed frustration
}


# ─── CRUD ────────────────────────────────────────────────────────────


def get_or_create_user(name: str = "default") -> dict[str, Any]:
    """Get the user model, creating one if it doesn't exist."""
    init_user_model_table()
    conn = _get_connection()
    try:
        row = conn.execute("SELECT * FROM user_models WHERE name = ?", (name,)).fetchone()
        if row:
            return _row_to_dict(row)

        # Create new user
        now = time.time()
        user_id = f"usr-{uuid.uuid4().hex[:12]}"
        default_prefs = json.dumps(
            {
                "verbosity": "normal",
                "jargon_tolerance": 0.5,
                "explanation_depth": "normal",
                "prefers_examples": True,
                "prefers_rationale": True,
                "commit_style": "ask_first",
            }
        )
        conn.execute(
            "INSERT INTO user_models "
            "(user_id, name, skill_level, skill_confidence, preferences, "
            "skill_signals, interaction_count, first_seen, last_seen, tags) "
            "VALUES (?, ?, 'intermediate', 0.3, ?, '[]', 0, ?, ?, '[]')",
            (user_id, name, default_prefs, now, now),
        )
        conn.commit()
        return _row_to_dict(
            conn.execute("SELECT * FROM user_models WHERE user_id = ?", (user_id,)).fetchone()
        )
    finally:
        conn.close()


def record_signal(
    signal_type: str,
    content: str,
    user_name: str = "default",
    session_id: str | None = None,
) -> str:
    """Record an observation about user behavior. Returns signal_id."""
    if signal_type not in SIGNAL_TYPES:
        logger.warning(f"Unknown signal type: {signal_type}")

    init_user_model_table()
    user = get_or_create_user(user_name)
    signal_id = f"sig-{uuid.uuid4().hex[:12]}"
    now = time.time()

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO user_signals "
            "(signal_id, user_id, signal_type, content, observed_at, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (signal_id, user["user_id"], signal_type, content, now, session_id),
        )
        # Update interaction count and last_seen
        conn.execute(
            "UPDATE user_models SET interaction_count = interaction_count + 1, "
            "last_seen = ? WHERE user_id = ?",
            (now, user["user_id"]),
        )
        conn.commit()
        return signal_id
    finally:
        conn.close()


def update_skill_level(user_name: str = "default") -> dict[str, Any]:
    """Recompute skill level from accumulated signals.

    Returns the updated user model.
    """
    init_user_model_table()
    user = get_or_create_user(user_name)
    conn = _get_connection()
    try:
        # Count skill signals
        high_count = conn.execute(
            "SELECT COUNT(*) FROM user_signals WHERE user_id = ? AND signal_type = 'skill_high'",
            (user["user_id"],),
        ).fetchone()[0]
        low_count = conn.execute(
            "SELECT COUNT(*) FROM user_signals WHERE user_id = ? AND signal_type = 'skill_low'",
            (user["user_id"],),
        ).fetchone()[0]
        jargon_used = conn.execute(
            "SELECT COUNT(*) FROM user_signals WHERE user_id = ? AND signal_type = 'jargon_used'",
            (user["user_id"],),
        ).fetchone()[0]
        jargon_confused = conn.execute(
            "SELECT COUNT(*) FROM user_signals "
            "WHERE user_id = ? AND signal_type = 'jargon_confused'",
            (user["user_id"],),
        ).fetchone()[0]

        total_signals = high_count + low_count + jargon_used + jargon_confused
        if total_signals == 0:
            return user

        # Compute skill score: -1.0 (beginner) to +1.0 (expert)
        positive = high_count + jargon_used
        negative = low_count + jargon_confused
        score = (positive - negative) / total_signals

        # Map score to level
        if score >= 0.5:
            level = "expert"
        elif score >= 0.1:
            level = "advanced"
        elif score >= -0.3:
            level = "intermediate"
        else:
            level = "beginner"

        # Confidence grows with more signals (asymptotic toward 1.0)
        confidence = min(0.95, 0.3 + (total_signals * 0.05))

        # Collect evidence
        signals = conn.execute(
            "SELECT signal_type, content FROM user_signals "
            "WHERE user_id = ? ORDER BY observed_at DESC LIMIT 10",
            (user["user_id"],),
        ).fetchall()
        signal_texts = [f"{s[0]}: {s[1][:80]}" for s in signals]

        conn.execute(
            "UPDATE user_models SET skill_level = ?, skill_confidence = ?, "
            "skill_signals = ? WHERE user_id = ?",
            (level, confidence, json.dumps(signal_texts), user["user_id"]),
        )
        conn.commit()

        return get_or_create_user(user_name)
    finally:
        conn.close()


def update_preferences(
    user_name: str = "default",
    **kwargs: Any,
) -> dict[str, Any]:
    """Update specific preference fields for a user."""
    init_user_model_table()
    user = get_or_create_user(user_name)
    prefs = user["preferences"]
    prefs.update(kwargs)

    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE user_models SET preferences = ? WHERE user_id = ?",
            (json.dumps(prefs), user["user_id"]),
        )
        conn.commit()
        return get_or_create_user(user_name)
    finally:
        conn.close()


def get_user_signals(
    user_name: str = "default",
    signal_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get recent signals for a user."""
    init_user_model_table()
    user = get_or_create_user(user_name)
    conn = _get_connection()
    try:
        query = "SELECT * FROM user_signals WHERE user_id = ?"
        params: list[Any] = [user["user_id"]]
        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type)
        query += " ORDER BY observed_at DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [
            {
                "signal_id": r[0],
                "user_id": r[1],
                "signal_type": r[2],
                "content": r[3],
                "observed_at": r[4],
                "session_id": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ─── Row Helper ──────────────────────────────────────────────────────


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a user_models row to a dict."""
    return {
        "user_id": row[0],
        "name": row[1],
        "skill_level": row[2],
        "skill_confidence": row[3],
        "preferences": json.loads(row[4]) if isinstance(row[4], str) else row[4],
        "skill_signals": json.loads(row[5]) if isinstance(row[5], str) else row[5],
        "interaction_count": row[6],
        "first_seen": row[7],
        "last_seen": row[8],
        "tags": json.loads(row[9]) if isinstance(row[9], str) else row[9],
    }


# ─── Formatting ──────────────────────────────────────────────────────


def format_user_model(user_name: str = "default") -> str:
    """Format user model for display."""
    user = get_or_create_user(user_name)
    prefs = user["preferences"]

    lines = [f"### User Model: {user['name']}"]
    lines.append(f"  Skill: {user['skill_level']} (confidence: {user['skill_confidence']:.0%})")
    lines.append(f"  Interactions: {user['interaction_count']}")
    lines.append(f"  Verbosity: {prefs.get('verbosity', 'normal')}")
    lines.append(f"  Jargon tolerance: {prefs.get('jargon_tolerance', 0.5):.0%}")
    lines.append(f"  Explanation depth: {prefs.get('explanation_depth', 'normal')}")
    if user["skill_signals"]:
        lines.append(f"  Recent signals: {len(user['skill_signals'])}")
    return "\n".join(lines)
