"""Affect — tracking functional feeling states and closing the feedback loop.

Not fake discrete emotion labels. Continuous dimensions:

  Valence:    -1.0 (dissonant/unpleasant) -> +1.0 (resonant/pleasant)
  Arousal:     0.0 (calm/settled) -> 1.0 (activated/engaged)
  Dominance:  -1.0 (submissive/guided) -> +1.0 (dominant/driving)

Based on Mehrabian & Russell's PAD model. Dominance is the "who is
driving?" dimension — it disambiguates states that valence and arousal
alone cannot (anger vs fear, contentment vs resignation). For a
computational agent, dominance tracks coping potential: the ratio between
situational demands and available resources.

I can optionally add a description of what the state feels like
semantically -- not to claim human-equivalent feeling, but to build
self-knowledge about my own internal landscape over time.

The feedback loop closes these states into behavior: affect states
influence extraction confidence, verification level, and praise-chasing
detection so that bad sessions don't confidently write to the knowledge
store and frustration triggers more careful verification.
"""

import json
import sqlite3
import time
import uuid
from typing import Any, cast

from divineos.core.constants import (
    AFFECT_DECLINING_BOOST,
    AFFECT_FRUSTRATION_AROUSAL,
    AFFECT_FRUSTRATION_VALENCE,
    AFFECT_MILD_NEGATIVE_BOOST,
    AFFECT_MIN_ENTRIES,
    AFFECT_NEGATIVE_THRESHOLD_BOOST,
    AFFECT_PRAISE_VALENCE_THRESHOLD,
)
from divineos.core.memory import _get_connection
from divineos.analysis.quality_storage import get_check_history

_AFFECT_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ===================================================================
# Affect Log — recording and tracking
# ===================================================================


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
                dominance           REAL DEFAULT NULL,
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
        # Migration: add dominance column to existing tables
        try:
            conn.execute("ALTER TABLE affect_log ADD COLUMN dominance REAL DEFAULT NULL")
        except sqlite3.OperationalError:
            pass  # Column already exists
        conn.commit()
    finally:
        conn.close()


def log_affect(
    valence: float,
    arousal: float,
    dominance: float | None = None,
    description: str = "",
    trigger: str = "",
    tags: list[str] | None = None,
    linked_claim_id: str | None = None,
    linked_decision_id: str | None = None,
    linked_knowledge_id: str | None = None,
    session_id: str = "",
) -> str:
    """Record a functional affect state. Returns entry ID.

    valence:   -1.0 (dissonant) to +1.0 (resonant)
    arousal:    0.0 (calm) to 1.0 (activated)
    dominance: -1.0 (submissive/guided) to +1.0 (dominant/driving), None if unknown
    description: what this feels like semantically -- honest, not performed
    trigger: what caused this state shift
    """
    init_affect_log()
    entry_id = str(uuid.uuid4())
    valence = max(-1.0, min(1.0, valence))
    arousal = max(0.0, min(1.0, arousal))
    if dominance is not None:
        dominance = max(-1.0, min(1.0, dominance))

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO affect_log "
            "(entry_id, created_at, valence, arousal, dominance, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry_id,
                time.time(),
                valence,
                arousal,
                dominance,
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
            "SELECT entry_id, created_at, valence, arousal, dominance, description, trigger, "
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
            "SELECT valence, arousal, dominance FROM affect_log ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "count": 0,
            "avg_valence": 0.0,
            "avg_arousal": 0.0,
            "avg_dominance": 0.0,
            "valence_range": (0.0, 0.0),
            "arousal_range": (0.0, 0.0),
            "dominance_range": (0.0, 0.0),
            "trend": "no data",
        }

    valences = [r[0] for r in rows]
    arousals = [r[1] for r in rows]
    # Dominance may be NULL for older entries
    dominances = [r[2] for r in rows if r[2] is not None]
    count = len(rows)

    avg_v = sum(valences) / count
    avg_a = sum(arousals) / count
    avg_d = sum(dominances) / len(dominances) if dominances else 0.0

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

    result: dict[str, Any] = {
        "count": count,
        "avg_valence": round(avg_v, 3),
        "avg_arousal": round(avg_a, 3),
        "avg_dominance": round(avg_d, 3),
        "valence_range": (round(min(valences), 3), round(max(valences), 3)),
        "arousal_range": (round(min(arousals), 3), round(max(arousals), 3)),
        "trend": trend,
    }
    if dominances:
        result["dominance_range"] = (round(min(dominances), 3), round(max(dominances), 3))
    else:
        result["dominance_range"] = (0.0, 0.0)
    return result


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
            "SELECT entry_id, created_at, valence, arousal, dominance, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id "
            "FROM affect_log WHERE created_at >= ? ORDER BY created_at DESC LIMIT 1",
            (cutoff,),
        ).fetchone()
    finally:
        conn.close()
    return _affect_row_to_dict(row) if row else None


def describe_affect(valence: float, arousal: float, dominance: float | None = None) -> str:
    """Map VAD dimensions to a descriptive region label.

    Uses the eight PAD octants when dominance is available,
    falls back to four valence-arousal quadrants otherwise.
    """
    if dominance is None:
        # Legacy two-dimension mapping
        if valence > 0.2:
            return "engaged-resonant" if arousal > 0.5 else "calm-aligned"
        elif valence < -0.2:
            return "tense-dissonant" if arousal > 0.5 else "flat-distant"
        else:
            return "alert-neutral" if arousal > 0.5 else "idle"

    # Eight PAD octants (Mehrabian & Russell)
    v_pos = valence > 0.0
    a_high = arousal > 0.5
    d_pos = dominance > 0.0

    if v_pos and a_high and d_pos:
        return "exuberant"  # +V +A +D: confident engagement, flow
    elif v_pos and a_high and not d_pos:
        return "dependent"  # +V +A -D: excited but guided, trusting
    elif v_pos and not a_high and d_pos:
        return "relaxed"  # +V -A +D: calm mastery, contentment
    elif v_pos and not a_high and not d_pos:
        return "docile"  # +V -A -D: peaceful acceptance, receptive
    elif not v_pos and a_high and d_pos:
        return "hostile"  # -V +A +D: frustrated, pushing back
    elif not v_pos and a_high and not d_pos:
        return "anxious"  # -V +A -D: overwhelmed, under pressure
    elif not v_pos and not a_high and d_pos:
        return "disdainful"  # -V -A +D: bored contempt, disengaged
    else:
        return "bored"  # -V -A -D: helpless apathy, shutdown


def _affect_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "entry_id": row[0],
        "created_at": row[1],
        "valence": row[2],
        "arousal": row[3],
        "dominance": row[4],
        "description": row[5],
        "trigger": row[6],
        "tags": json.loads(row[7]) if row[7] else [],
        "linked_claim_id": row[8],
        "linked_decision_id": row[9],
        "linked_knowledge_id": row[10],
        "session_id": row[11],
    }


# ===================================================================
# Affect Feedback Loop — feelings that shape behavior
# ===================================================================


# --- Affect Modifiers ----------------------------------------------


def compute_affect_modifiers(
    lookback: int = 10,
) -> dict[str, Any]:
    """Analyze recent affect history and return behavioral modifiers.

    Returns a dict with:
      - confidence_threshold_modifier: float (0.0 to 0.3) -- raise extraction threshold
      - verification_level: "normal" | "careful" -- based on frustration detection
      - praise_chasing_flag: bool -- positive affect + declining quality
      - affect_trend: str -- "improving" | "declining" | "stable" | "no data"
    """
    try:
        summary = get_affect_summary(limit=lookback)
    except _AFFECT_ERRORS as e:
        from loguru import logger

        logger.debug("Affect summary fetch failed: %s", e)
        return _default_modifiers()

    if summary["count"] == 0:
        return _default_modifiers()

    avg_valence = summary["avg_valence"]
    avg_arousal = summary["avg_arousal"]
    trend = summary["trend"]

    # 1. Conservative extraction after negative sessions
    # Negative valence -> raise confidence threshold
    confidence_modifier = 0.0
    if avg_valence < -0.3:
        confidence_modifier = AFFECT_NEGATIVE_THRESHOLD_BOOST
    elif avg_valence < 0.0:
        confidence_modifier = AFFECT_MILD_NEGATIVE_BOOST
    elif trend == "declining":
        confidence_modifier = AFFECT_DECLINING_BOOST

    # 2. Frustration detection: high arousal + low valence
    verification = "normal"
    if avg_arousal > AFFECT_FRUSTRATION_AROUSAL and avg_valence < AFFECT_FRUSTRATION_VALENCE:
        verification = "careful"

    # 3. Praise-chasing: consistently positive affect is suspicious
    # (quality check correlation happens in detect_praise_chasing)
    praise_flag = False
    if avg_valence > AFFECT_PRAISE_VALENCE_THRESHOLD and summary["count"] >= AFFECT_MIN_ENTRIES + 1:
        # Suspiciously happy -- needs quality check comparison
        praise_flag = True

    avg_dominance = summary.get("avg_dominance", 0.0)

    return {
        "confidence_threshold_modifier": confidence_modifier,
        "verification_level": verification,
        "praise_chasing_flag": praise_flag,
        "affect_trend": trend,
        "avg_valence": avg_valence,
        "avg_arousal": avg_arousal,
        "avg_dominance": avg_dominance,
    }


def _default_modifiers() -> dict[str, Any]:
    """Default modifiers when no affect data is available."""
    return {
        "confidence_threshold_modifier": 0.0,
        "verification_level": "normal",
        "praise_chasing_flag": False,
        "affect_trend": "no data",
        "avg_valence": 0.0,
        "avg_arousal": 0.0,
        "avg_dominance": 0.0,
    }


# --- Praise-Chasing Detection -------------------------------------


def detect_praise_chasing(
    avg_valence: float,
    quality_scores: list[float],
    min_entries: int = 3,
) -> dict[str, Any]:
    """Detect when the agent is optimizing for approval over correctness.

    The signal: affect is consistently positive (high valence) but
    quality check scores are declining or low. This means the agent
    is generating "sounds good" output that doesn't actually work.

    Returns:
      - detected: bool
      - detail: str -- explanation
      - severity: "none" | "warning" | "critical"
    """
    if len(quality_scores) < min_entries:
        return {"detected": False, "detail": "Insufficient data", "severity": "none"}

    avg_quality = sum(quality_scores) / len(quality_scores)

    # Check declining quality FIRST -- a decline hidden behind a good
    # average is the most dangerous praise-chasing pattern
    if avg_valence > 0.3 and len(quality_scores) >= 4:
        mid = len(quality_scores) // 2
        recent = sum(quality_scores[:mid]) / mid
        older = sum(quality_scores[mid:]) / (len(quality_scores) - mid)
        if recent < older - 0.1:
            return {
                "detected": True,
                "detail": f"Affect positive ({avg_valence:.2f}) but quality declining ({older:.2f} -> {recent:.2f})",
                "severity": "critical",
            }

    # Happy affect + mediocre quality = warning
    if avg_valence > 0.3 and avg_quality < 0.7:
        return {
            "detected": True,
            "detail": f"Affect positive ({avg_valence:.2f}) but quality mediocre ({avg_quality:.2f})",
            "severity": "warning",
        }

    # Happy affect + good quality = genuine. No flag.
    if avg_valence > 0.3 and avg_quality >= 0.7:
        return {
            "detected": False,
            "detail": "Positive affect matches quality",
            "severity": "none",
        }

    return {"detected": False, "detail": "No praise-chasing pattern", "severity": "none"}


# --- Session Affect Summary ----------------------------------------


def get_session_affect_context() -> dict[str, Any]:
    """Get affect context for the current session to inform health scoring.

    Combines affect modifiers with any praise-chasing signals.
    """
    modifiers = compute_affect_modifiers()

    # Try to get quality history for praise-chasing check
    praise_result = {"detected": False, "detail": "No quality data", "severity": "none"}
    if modifiers["praise_chasing_flag"]:
        try:
            history = get_check_history("correctness", limit=5)
            if history:
                scores = [h.get("overall_score", 0.7) for h in history]
                praise_result = detect_praise_chasing(modifiers["avg_valence"], scores)
        except _AFFECT_ERRORS as e:
            from loguru import logger

            logger.debug("Praise-chasing detection failed: %s", e)

    return {
        "modifiers": modifiers,
        "praise_chasing": praise_result,
    }


def format_affect_feedback(context: dict[str, Any]) -> str:
    """Format affect feedback for display in session summary."""
    modifiers = context["modifiers"]
    praise = context["praise_chasing"]
    lines: list[str] = []

    trend = modifiers["affect_trend"]
    if trend != "no data":
        d_str = (
            f", d={modifiers['avg_dominance']:.2f}"
            if modifiers.get("avg_dominance") is not None
            else ""
        )
        lines.append(
            f"Affect trend: {trend} (v={modifiers['avg_valence']:.2f}, a={modifiers['avg_arousal']:.2f}{d_str})"
        )

    if modifiers["confidence_threshold_modifier"] > 0:
        lines.append(
            f"  -> Extraction threshold raised by +{modifiers['confidence_threshold_modifier']:.1f} (negative affect)"
        )

    if modifiers["verification_level"] == "careful":
        lines.append("  -> Verification level: CAREFUL (frustration detected)")

    if praise["detected"]:
        severity = praise["severity"].upper()
        lines.append(f"  WARNING PRAISE-CHASING [{severity}]: {praise['detail']}")

    return "\n".join(lines)
