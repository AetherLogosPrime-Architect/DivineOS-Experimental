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

import sqlite3
from typing import Any

from divineos.core.knowledge import _get_connection

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


def _get_session_metrics(limit: int = 10) -> list[dict[str, Any]]:
    """Recent per-session metric rows, newest first, from session_history.

    This is the real per-session data source — structured counts written at
    extract time. The earlier version grepped ledger consolidation payloads
    for text ("grade: x", "corrected N time") that those payloads never
    contained, so every trend silently returned "insufficient data"
    (claim 3cffa9dc). session_history holds the actual numbers.
    """
    try:
        from divineos.core.growth import get_session_history

        return get_session_history(limit=limit)
    except _DRIFT_ERRORS as e:
        from loguru import logger

        logger.debug("Session metrics fetch failed: %s", e)
        return []


# ─── Correction Trend Detection ──────────────────────────────────


def detect_correction_trend(
    min_sessions: int = 3,
    sessions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Check if corrections are rising over recent sessions.

    Reads real per-session correction counts from session_history (newest
    first). Surfaces the trend numbers; the "increasing" flag is a threshold
    over real data pointing at where to look — the judgment of whether a
    rise matters, and why, stays with the agent. Accepts an injected
    ``sessions`` list (newest first) for testing.

    "Quality declining over sessions" used to be its own grade-trend detector;
    it trended the composite grade, which is noise (decision 58e5ad1d). Rising
    corrections is the honest, evidence-based version of the same signal, so
    that's the one signal we keep.
    """
    rows = sessions if sessions is not None else _get_session_metrics()

    counts = [int(r.get("corrections", 0)) for r in rows if "corrections" in r]
    if len(counts) < min_sessions:
        return {"increasing": False, "detail": "Not enough sessions"}

    # rows are newest-first → counts[:midpoint] is the recent half.
    midpoint = len(counts) // 2
    recent_avg = sum(counts[:midpoint]) / max(midpoint, 1)
    older_avg = sum(counts[midpoint:]) / max(len(counts) - midpoint, 1)

    increasing = recent_avg > older_avg + 2

    return {
        "increasing": increasing,
        "recent_avg": round(recent_avg, 1),
        "older_avg": round(older_avg, 1),
        "delta": round(recent_avg - older_avg, 1),
        "session_count": len(counts),
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
    corrections = detect_correction_trend()

    drift_signals = 0
    if regressions:
        drift_signals += len(regressions)
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

    corrections = report["correction_trend"]
    if corrections.get("increasing"):
        lines.append(f"\nCorrection trend: {corrections['detail']}")

    return "\n".join(lines)
