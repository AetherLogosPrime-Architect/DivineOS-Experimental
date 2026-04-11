"""Drift Detection — catch when behavior diverges from stated principles.

The agent has principles in its knowledge store. This module checks
whether recent behavior actually follows those principles or has
drifted away from them.

Three drift signals:

1. LESSON REGRESSION: A lesson was marked "improving" but the same
   pattern recurred. The agent learned the lesson but didn't stick to it.

2. QUALITY TREND: Session grades declining over time — the agent is
   getting worse, not better.

3. CORRECTION TREND: Corrections increasing over time — the agent is
   making more mistakes, not fewer.
"""

import json
import re
import sqlite3
from typing import Any

from divineos.core.knowledge._base import _get_connection
from divineos.core.ledger import get_events

_DRIFT_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ─── Lesson Regression Detection ──────────────────────────────────


def detect_lesson_regressions(lookback: int = 5) -> list[dict[str, Any]]:
    """Find lessons that have actually regressed — improving then re-fired.

    Measures CHANGE (regression events) not STATE (occurrence count).
    A lesson with 50 occurrences but 0 regressions is not drifting —
    it's a chronic issue that hasn't been addressed yet. A lesson with
    5 occurrences and 3 regressions IS drifting — the agent keeps
    cycling between "improving" and "active".

    Also catches active lessons with high regression counts, which
    indicate the lesson repeatedly enters improving then falls back.
    """
    conn = _get_connection()
    try:
        # Ensure the regressions column exists (added in a migration)
        try:
            conn.execute(
                "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Query both improving and active lessons that have regressed.
        # The regressions column tracks actual regression events (improving -> active).
        try:
            rows = conn.execute(
                """SELECT lesson_id, category, description, occurrences, status, regressions
                   FROM lesson_tracking
                   WHERE regressions > 0
                   ORDER BY regressions DESC
                   LIMIT ?""",
                (lookback * 10,),
            ).fetchall()
        except _DRIFT_ERRORS:
            # Fallback if regressions column still missing somehow
            rows = conn.execute(
                """SELECT lesson_id, category, description, occurrences, status, 0
                   FROM lesson_tracking
                   WHERE status = 'improving' AND occurrences >= 5
                   ORDER BY occurrences DESC
                   LIMIT ?""",
                (lookback * 10,),
            ).fetchall()
    except _DRIFT_ERRORS as e:
        from loguru import logger

        logger.debug("Lesson regression query failed: %s", e)
        return []
    finally:
        conn.close()

    regressions: list[dict[str, Any]] = []
    for row in rows:
        occurrences = row[3]
        regression_count = row[5]
        regressions.append(
            {
                "type": "lesson_regression",
                "lesson_id": row[0],
                "category": row[1],
                "description": row[2],
                "occurrences": occurrences,
                "regressions": regression_count,
                "status": row[4],
                "severity": "high" if regression_count >= 3 else "medium",
                "detail": (
                    f"Lesson '{row[2][:60]}' regressed {regression_count}x "
                    f"({occurrences} total occurrences)"
                ),
            }
        )

    return regressions


# ─── Session History Fetching ─────────────────────────────────────


def _get_session_payloads(limit: int = 10) -> list[str]:
    """Get recent SESSION_END payloads from the ledger.

    Tries the ledger (system_events) first, falls back gracefully.
    """
    try:
        events = get_events(limit=limit, event_type="SESSION_END")
        # Reverse to get newest first
        events.reverse()
        payloads: list[str] = []
        for e in events:
            payload = e.get("payload", {})
            if isinstance(payload, dict):
                payloads.append(json.dumps(payload))
            else:
                payloads.append(str(payload))
        return payloads
    except _DRIFT_ERRORS as e:
        from loguru import logger

        logger.debug("Session payload fetch failed: %s", e)
        return []


# ─── Quality Trend Detection ─────────────────────────────────────


def detect_quality_drift(
    min_sessions: int = 3,
    session_payloads: list[str] | None = None,
) -> dict[str, Any]:
    """Check if session quality is declining over time.

    Accepts pre-fetched payloads for testing, or fetches from ledger.
    """
    payloads = session_payloads if session_payloads is not None else _get_session_payloads()

    if len(payloads) < min_sessions:
        return {"drifting": False, "detail": "Not enough sessions for trend analysis"}

    grade_map = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
    grades: list[int] = []

    for payload in payloads:
        payload_lower = payload.lower()
        for grade_letter, grade_val in grade_map.items():
            if (
                f"grade: {grade_letter.lower()}" in payload_lower
                or f"grade {grade_letter.lower()}" in payload_lower
            ):
                grades.append(grade_val)
                break

    if len(grades) < min_sessions:
        return {"drifting": False, "detail": "Not enough graded sessions"}

    midpoint = len(grades) // 2
    recent_avg = sum(grades[:midpoint]) / max(midpoint, 1)
    older_avg = sum(grades[midpoint:]) / max(len(grades) - midpoint, 1)

    declining = recent_avg < older_avg - 0.5

    return {
        "drifting": declining,
        "recent_avg": round(recent_avg, 2),
        "older_avg": round(older_avg, 2),
        "delta": round(recent_avg - older_avg, 2),
        "grade_count": len(grades),
        "detail": (
            f"Quality declining: recent avg {recent_avg:.1f} vs older avg {older_avg:.1f}"
            if declining
            else f"Quality stable: recent avg {recent_avg:.1f} vs older avg {older_avg:.1f}"
        ),
    }


# ─── Correction Trend Detection ──────────────────────────────────


def detect_correction_trend(
    min_sessions: int = 3,
    session_payloads: list[str] | None = None,
) -> dict[str, Any]:
    """Check if corrections are increasing over time.

    Accepts pre-fetched payloads for testing, or fetches from ledger.
    """
    payloads = session_payloads if session_payloads is not None else _get_session_payloads()

    if len(payloads) < min_sessions:
        return {"increasing": False, "detail": "Not enough sessions"}

    corrections: list[int] = []
    for payload in payloads:
        match = re.search(r"corrected (\d+) time", payload)
        if match:
            corrections.append(int(match.group(1)))

    if len(corrections) < min_sessions:
        return {"increasing": False, "detail": "Not enough correction data"}

    midpoint = len(corrections) // 2
    recent_avg = sum(corrections[:midpoint]) / max(midpoint, 1)
    older_avg = sum(corrections[midpoint:]) / max(len(corrections) - midpoint, 1)

    increasing = recent_avg > older_avg + 2

    return {
        "increasing": increasing,
        "recent_avg": round(recent_avg, 1),
        "older_avg": round(older_avg, 1),
        "delta": round(recent_avg - older_avg, 1),
        "detail": (
            f"Corrections rising: recent avg {recent_avg:.1f} vs older avg {older_avg:.1f}"
            if increasing
            else f"Corrections stable: recent avg {recent_avg:.1f} vs older avg {older_avg:.1f}"
        ),
    }


# ─── Full Drift Report ───────────────────────────────────────────


def run_drift_detection() -> dict[str, Any]:
    """Run all drift detection checks."""
    regressions = detect_lesson_regressions()
    quality = detect_quality_drift()
    corrections = detect_correction_trend()

    drift_signals = 0
    if regressions:
        drift_signals += len(regressions)
    if quality.get("drifting"):
        drift_signals += 2
    if corrections.get("increasing"):
        drift_signals += 1

    if drift_signals == 0:
        severity = "none"
    elif drift_signals <= 2:
        severity = "low"
    elif drift_signals <= 4:
        severity = "medium"
    else:
        severity = "high"

    return {
        "regressions": regressions,
        "quality_drift": quality,
        "correction_trend": corrections,
        "drift_signals": drift_signals,
        "severity": severity,
    }


def format_drift_report(report: dict[str, Any]) -> str:
    """Format drift report for display."""
    lines: list[str] = []

    severity = report["severity"]
    if severity == "none":
        return "No drift detected — behavior aligns with principles."

    lines.append(f"Drift severity: {severity.upper()} ({report['drift_signals']} signal(s))\n")

    if report["regressions"]:
        lines.append("Lesson regressions:")
        for reg in report["regressions"]:
            lines.append(f"  ⚠ {reg['detail']}")

    quality = report["quality_drift"]
    if quality.get("drifting"):
        lines.append(f"\nQuality drift: {quality['detail']}")

    corrections = report["correction_trend"]
    if corrections.get("increasing"):
        lines.append(f"\nCorrection trend: {corrections['detail']}")

    return "\n".join(lines)
