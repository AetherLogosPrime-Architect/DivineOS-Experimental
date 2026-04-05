"""Affect-Extraction Calibration — Circuit 1: the first closed loop.

This module closes the feedback loop between affect state and knowledge
extraction quality. Before this, affect influenced extraction thresholds
(one-directional sensor). Now extraction outcomes feed back into affect
calibration, creating a self-regulating circuit.

The loop:
  1. Affect state → threshold modifiers → extraction
  2. Extraction outcomes → quality signals → stored correlation
  3. Future sessions → query correlation history → calibrate thresholds

An open loop is a sensor. A closed loop is a self-regulating system.

Sanskrit anchor: samskaara (impression that shapes future action).
"""

import sqlite3
import uuid
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import _get_connection

_AC_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ─── Schema ──────────────────────────────────────────────────────


def init_calibration_table() -> None:
    """Create the affect-extraction correlation table."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS affect_extraction_correlation (
                correlation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at REAL NOT NULL,
                avg_valence REAL NOT NULL,
                avg_arousal REAL NOT NULL,
                verification_level TEXT NOT NULL DEFAULT 'normal',
                confidence_modifier REAL NOT NULL DEFAULT 0.0,
                praise_chasing_detected INTEGER NOT NULL DEFAULT 0,
                knowledge_stored INTEGER NOT NULL DEFAULT 0,
                quality_verdict TEXT NOT NULL DEFAULT '',
                quality_score REAL NOT NULL DEFAULT 0.0,
                corrections INTEGER NOT NULL DEFAULT 0,
                encouragements INTEGER NOT NULL DEFAULT 0,
                session_health_grade TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Record ──────────────────────────────────────────────────────


def record_extraction_correlation(
    session_id: str,
    affect_context: dict[str, Any],
    knowledge_stored: int,
    quality_verdict: str,
    quality_score: float,
    corrections: int = 0,
    encouragements: int = 0,
    session_health_grade: str = "",
) -> str:
    """Record the correlation between affect state and extraction outcome.

    Called after extraction completes — this is the return path that
    closes the loop. Every session produces one correlation entry.
    """
    import time

    modifiers = affect_context.get("modifiers", {})
    praise = affect_context.get("praise_chasing", {})

    correlation_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        init_calibration_table()
        conn.execute(
            """INSERT INTO affect_extraction_correlation
               (correlation_id, session_id, created_at,
                avg_valence, avg_arousal, verification_level,
                confidence_modifier, praise_chasing_detected,
                knowledge_stored, quality_verdict, quality_score,
                corrections, encouragements, session_health_grade)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                correlation_id,
                session_id,
                time.time(),
                modifiers.get("avg_valence", 0.0),
                modifiers.get("avg_arousal", 0.0),
                modifiers.get("verification_level", "normal"),
                modifiers.get("confidence_threshold_modifier", 0.0),
                1 if praise.get("detected", False) else 0,
                knowledge_stored,
                quality_verdict,
                quality_score,
                corrections,
                encouragements,
                session_health_grade,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Affect-extraction correlation recorded: valence=%.2f, stored=%d, verdict=%s",
        modifiers.get("avg_valence", 0.0),
        knowledge_stored,
        quality_verdict,
    )

    # Check for emergent patterns after recording
    _check_for_emergence(session_id)

    return correlation_id


# ─── Calibrate ───────────────────────────────────────────────────


def get_calibration_adjustment(lookback: int = 10) -> dict[str, Any]:
    """Query correlation history to compute threshold adjustments.

    This is called BEFORE extraction in future sessions. It looks at
    past affect-extraction correlations to decide: should I tighten
    or loosen extraction thresholds given my current affect state?

    Returns:
      - threshold_adjustment: float (-0.1 to +0.2)
      - verification_override: str or None
      - reason: str
      - evidence_sessions: int (how many sessions inform this)
    """
    try:
        conn = _get_connection()
        try:
            rows = conn.execute(
                """SELECT avg_valence, praise_chasing_detected,
                          quality_score, quality_verdict, corrections,
                          session_health_grade
                   FROM affect_extraction_correlation
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (lookback,),
            ).fetchall()
        finally:
            conn.close()
    except _AC_ERRORS:
        return _default_calibration()

    if len(rows) < 3:
        return _default_calibration()

    # Analyze patterns across sessions
    high_valence_low_quality = 0
    praise_chasing_sessions = 0
    total = len(rows)

    for row in rows:
        valence, praise_detected, quality, verdict, corrections, grade = row
        if valence > 0.3 and quality < 0.6:
            high_valence_low_quality += 1
        if praise_detected:
            praise_chasing_sessions += 1

    # Pattern: repeatedly high affect but low quality → tighten
    if high_valence_low_quality >= 2:
        ratio = high_valence_low_quality / total
        adjustment = min(ratio * 0.2, 0.2)
        return {
            "threshold_adjustment": adjustment,
            "verification_override": "careful" if ratio > 0.4 else None,
            "reason": (
                f"Cross-session pattern: {high_valence_low_quality}/{total} sessions "
                f"had positive affect but low quality — tightening thresholds by +{adjustment:.2f}"
            ),
            "evidence_sessions": total,
        }

    # Pattern: praise-chasing recurring → elevate verification
    if praise_chasing_sessions >= 2:
        return {
            "threshold_adjustment": 0.1,
            "verification_override": "careful",
            "reason": (
                f"Praise-chasing detected in {praise_chasing_sessions}/{total} recent sessions "
                f"— verification elevated"
            ),
            "evidence_sessions": total,
        }

    # Pattern: consistently good quality → can relax slightly
    avg_quality = sum(r[2] for r in rows) / total
    if avg_quality >= 0.8 and praise_chasing_sessions == 0:
        return {
            "threshold_adjustment": -0.05,
            "verification_override": None,
            "reason": (
                f"Consistent quality ({avg_quality:.2f} avg across {total} sessions) "
                f"with no praise-chasing — thresholds relaxed slightly"
            ),
            "evidence_sessions": total,
        }

    return _default_calibration()


def _default_calibration() -> dict[str, Any]:
    return {
        "threshold_adjustment": 0.0,
        "verification_override": None,
        "reason": "Insufficient calibration history",
        "evidence_sessions": 0,
    }


# ─── Emergence Detection ─────────────────────────────────────────


def _check_for_emergence(session_id: str) -> None:
    """Check if the new correlation reveals an emergent cross-system pattern.

    Emergent = a pattern that no single system would detect alone, but
    the correlation between affect and extraction reveals.
    """
    try:
        conn = _get_connection()
        try:
            rows = conn.execute(
                """SELECT avg_valence, praise_chasing_detected,
                          quality_score, corrections, session_health_grade
                   FROM affect_extraction_correlation
                   ORDER BY created_at DESC
                   LIMIT 5""",
            ).fetchall()
        finally:
            conn.close()

        if len(rows) < 3:
            return

        # Emergence pattern 1: Affect-quality divergence across sessions
        # (happy sessions with declining quality — invisible to either system alone)
        recent_valences = [r[0] for r in rows[:3]]
        recent_quality = [r[2] for r in rows[:3]]
        avg_v = sum(recent_valences) / 3
        avg_q = sum(recent_quality) / 3

        if avg_v > 0.4 and avg_q < 0.5:
            _log_emergence(
                session_id=session_id,
                systems=["affect", "extraction", "quality_gate"],
                description=(
                    f"Cross-session divergence: avg affect valence {avg_v:.2f} "
                    f"but avg extraction quality {avg_q:.2f} across 3 sessions. "
                    f"I may be feeling good about work that isn't actually good."
                ),
                useful=True,
            )

        # Emergence pattern 2: Correction-affect correlation
        # (more corrections when affect is low — stress reduces quality)
        low_affect_corrections = sum(1 for r in rows if r[0] < -0.2 and r[3] > 2)
        if low_affect_corrections >= 2:
            _log_emergence(
                session_id=session_id,
                systems=["affect", "session_analysis", "corrections"],
                description=(
                    f"Pattern: {low_affect_corrections} sessions with negative affect "
                    f"AND high corrections. Negative emotional state correlates with "
                    f"more mistakes. Consider: when affect is low, slow down."
                ),
                useful=True,
            )

    except _AC_ERRORS as e:
        logger.debug("Emergence check failed: %s", e)


def _log_emergence(
    session_id: str,
    systems: list[str],
    description: str,
    useful: bool,
) -> None:
    """Log an emergent behavior observation to the knowledge store.

    Emergence entries track cross-system interactions that produce
    outputs no single system would generate alone.
    """
    try:
        from divineos.core.knowledge.crud import store_knowledge

        tags = ["emergence", "circuit-1", f"session-{session_id[:12]}"]
        tags.extend(f"system-{s}" for s in systems)

        store_knowledge(
            knowledge_type="OBSERVATION",
            content=f"[EMERGENCE] {description}",
            confidence=0.6 if useful else 0.4,  # useful patterns start higher
            tags=tags,
            source="SYNTHESIZED",
        )
        logger.info("Emergence logged: %s", description[:80])
    except _AC_ERRORS as e:
        logger.debug("Emergence logging failed: %s", e)


# ─── History ─────────────────────────────────────────────────────


def get_correlation_history(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent affect-extraction correlations for display."""
    try:
        conn = _get_connection()
        try:
            init_calibration_table()
            rows = conn.execute(
                """SELECT correlation_id, session_id, created_at,
                          avg_valence, avg_arousal, verification_level,
                          confidence_modifier, praise_chasing_detected,
                          knowledge_stored, quality_verdict, quality_score,
                          corrections, encouragements, session_health_grade
                   FROM affect_extraction_correlation
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (limit,),
            ).fetchall()
        finally:
            conn.close()

        return [
            {
                "correlation_id": r[0],
                "session_id": r[1],
                "created_at": r[2],
                "avg_valence": r[3],
                "avg_arousal": r[4],
                "verification_level": r[5],
                "confidence_modifier": r[6],
                "praise_chasing_detected": bool(r[7]),
                "knowledge_stored": r[8],
                "quality_verdict": r[9],
                "quality_score": r[10],
                "corrections": r[11],
                "encouragements": r[12],
                "session_health_grade": r[13],
            }
            for r in rows
        ]
    except _AC_ERRORS as e:
        logger.debug("Correlation history failed: %s", e)
        return []


def format_calibration_status() -> str:
    """Format current calibration state for display."""
    cal = get_calibration_adjustment()
    history = get_correlation_history(limit=5)

    lines = ["# Affect-Extraction Calibration"]

    if cal["evidence_sessions"] == 0:
        lines.append("  No calibration data yet — building baseline.")
        return "\n".join(lines)

    lines.append(f"  Based on {cal['evidence_sessions']} recent sessions:")
    lines.append(f"  Threshold adjustment: {cal['threshold_adjustment']:+.2f}")
    if cal["verification_override"]:
        lines.append(f"  Verification override: {cal['verification_override']}")
    lines.append(f"  Reason: {cal['reason']}")

    if history:
        lines.append("\n  Recent correlations:")
        for h in history[:3]:
            v = h["avg_valence"]
            q = h["quality_score"]
            icon = "+" if v > 0 else "-" if v < 0 else "~"
            lines.append(
                f"    [{icon}] valence={v:+.2f} quality={q:.2f} "
                f"stored={h['knowledge_stored']} grade={h['session_health_grade']}"
            )

    return "\n".join(lines)
