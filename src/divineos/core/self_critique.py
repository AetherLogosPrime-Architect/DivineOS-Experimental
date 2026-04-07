"""Self-Critique — periodic self-assessment of craft quality.

Goes beyond quality checks (which measure outcomes) to assess the
quality of reasoning, decision-making, and execution craft. Tracks
multiple "craft spectrums" over time to reveal patterns in how well
I'm thinking, not just what I'm producing.

The difference: quality checks ask "did the code work?" Self-critique
asks "was my approach to the problem elegant or brute-force?"

Runs automatically at SESSION_END, not on demand. The point is to
build a habit of reflection without being asked.

Sanskrit anchor: atma-pariksha (self-examination, introspective assessment).
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any


from divineos.core.knowledge._base import _get_connection

_SC_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Craft spectrums — dimensions of quality beyond correctness.
# Each spectrum is a -1.0 to +1.0 range.
CRAFT_SPECTRUMS = {
    "elegance": {
        "description": "brute-force (-1) ↔ elegant (+1)",
        "negative": "brute-force",
        "positive": "elegant",
    },
    "thoroughness": {
        "description": "surface-level (-1) ↔ deep (+1)",
        "negative": "surface-level",
        "positive": "deep",
    },
    "autonomy": {
        "description": "hand-held (-1) ↔ independent (+1)",
        "negative": "hand-held",
        "positive": "independent",
    },
    "proportionality": {
        "description": "over-engineered (-1) ↔ right-sized (+1)",
        "negative": "over-engineered",
        "positive": "right-sized",
    },
    "communication": {
        "description": "confusing (-1) ↔ clear (+1)",
        "negative": "confusing",
        "positive": "clear",
    },
}


@dataclass
class CraftAssessment:
    """A single self-assessment of craft quality."""

    assessment_id: str
    session_id: str
    scores: dict[str, float]  # spectrum_name → score (-1.0 to 1.0)
    overall: float  # weighted average
    notes: list[str]  # self-observations
    assessed_at: float


@dataclass
class CraftTrend:
    """Trend across recent assessments for a single spectrum."""

    spectrum: str
    recent_scores: list[float]
    average: float
    direction: str  # improving/declining/stable
    concern: str  # empty if fine, description if problematic


# ─── Schema ─────────────────────────────────────────────────────────


def init_critique_table() -> None:
    """Create self-critique tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS craft_assessments (
                assessment_id TEXT PRIMARY KEY,
                session_id    TEXT NOT NULL DEFAULT '',
                scores        TEXT NOT NULL DEFAULT '{}',
                overall       REAL NOT NULL DEFAULT 0.0,
                notes         TEXT NOT NULL DEFAULT '[]',
                assessed_at   REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_craft_session
            ON craft_assessments(session_id)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Assessment ──────────────────────────────────────────────────────


def assess_session_craft(session_id: str = "") -> CraftAssessment:
    """Run automatic self-critique for the current session.

    Computes craft scores from measurable session data:
    - Elegance: ratio of files read to files edited (more reading = more care)
    - Thoroughness: test count relative to code changes
    - Autonomy: OS consultation frequency (used the OS without being forced)
    - Proportionality: lines changed relative to problem size
    - Communication: corrections received (fewer = clearer communication)
    """
    import json

    init_critique_table()
    scores: dict[str, float] = {}
    notes: list[str] = []

    # Gather evidence from the session
    evidence = _gather_session_evidence()

    # Elegance: read-before-edit ratio
    reads = evidence.get("file_reads", 0)
    edits = evidence.get("file_edits", 0)
    if edits > 0:
        ratio = reads / edits
        # 2:1 read:edit = good (+0.5), 1:1 = neutral, 0:1 = bad (-0.5)
        scores["elegance"] = min(1.0, max(-1.0, (ratio - 1.0) * 0.5))
    else:
        scores["elegance"] = 0.0

    # Thoroughness: tests run relative to changes
    tests_run = evidence.get("tests_run", 0)
    if edits > 0:
        test_ratio = tests_run / max(edits, 1)
        scores["thoroughness"] = min(1.0, max(-1.0, test_ratio - 0.5))
    else:
        scores["thoroughness"] = 0.0

    # Autonomy: OS queries (ask, recall, decide) without being forced
    os_queries = evidence.get("os_queries", 0)
    gate_blocks = evidence.get("gate_blocks", 0)
    if os_queries > 0 and gate_blocks == 0:
        scores["autonomy"] = min(1.0, os_queries * 0.2)
        notes.append(f"Consulted OS {os_queries} times voluntarily.")
    elif gate_blocks > 0:
        scores["autonomy"] = max(-1.0, -0.3 * gate_blocks)
        notes.append(f"Gate blocked {gate_blocks} time(s) — need more self-direction.")
    else:
        scores["autonomy"] = 0.0

    # Proportionality: hard to measure automatically, default to neutral
    scores["proportionality"] = 0.0

    # Communication: corrections
    corrections = evidence.get("corrections", 0)
    encouragements = evidence.get("encouragements", 0)
    if corrections + encouragements > 0:
        # Ratio of positive to total feedback
        pos_ratio = encouragements / (corrections + encouragements)
        scores["communication"] = min(1.0, max(-1.0, (pos_ratio - 0.5) * 2))
    else:
        scores["communication"] = 0.0

    # Overall: weighted average
    weights = {
        "elegance": 0.2,
        "thoroughness": 0.25,
        "autonomy": 0.2,
        "proportionality": 0.15,
        "communication": 0.2,
    }
    overall = sum(scores.get(k, 0) * w for k, w in weights.items())

    assessment_id = f"ca-{uuid.uuid4().hex[:12]}"
    now = time.time()

    assessment = CraftAssessment(
        assessment_id=assessment_id,
        session_id=session_id,
        scores=scores,
        overall=round(overall, 3),
        notes=notes,
        assessed_at=now,
    )

    # Store
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO craft_assessments "
            "(assessment_id, session_id, scores, overall, notes, assessed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                assessment_id,
                session_id,
                json.dumps(scores),
                assessment.overall,
                json.dumps(notes),
                now,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    return assessment


def _gather_session_evidence() -> dict[str, int]:
    """Gather measurable evidence from the current session."""
    evidence: dict[str, int] = {
        "file_reads": 0,
        "file_edits": 0,
        "tests_run": 0,
        "os_queries": 0,
        "gate_blocks": 0,
        "corrections": 0,
        "encouragements": 0,
    }

    try:
        conn = _get_connection()
        try:
            # Count tool events from this session
            # Look at recent events (last 2 hours as proxy for "this session")
            cutoff = time.time() - 7200
            rows = conn.execute(
                "SELECT event_type, payload FROM system_events "
                "WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,),
            ).fetchall()

            for event_type, content in rows:
                content_lower = (content or "").lower()
                if event_type == "TOOL_CALL" and "read" in content_lower:
                    evidence["file_reads"] += 1
                elif event_type == "TOOL_CALL" and "edit" in content_lower:
                    evidence["file_edits"] += 1
                elif event_type == "TOOL_CALL" and "pytest" in content_lower:
                    evidence["tests_run"] += 1
                elif event_type == "USER_INPUT" and any(
                    cmd in content_lower for cmd in ("ask ", "recall", "decide ", "context")
                ):
                    evidence["os_queries"] += 1
        finally:
            conn.close()
    except _SC_ERRORS:
        pass

    return evidence


def get_craft_trends(n: int = 5) -> list[CraftTrend]:
    """Compute trends across recent craft assessments."""
    import json

    init_critique_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT scores FROM craft_assessments ORDER BY assessed_at DESC LIMIT ?",
            (n,),
        ).fetchall()

        if len(rows) < 2:
            return []

        # Collect scores per spectrum
        spectrum_scores: dict[str, list[float]] = {k: [] for k in CRAFT_SPECTRUMS}
        for row in rows:
            scores = json.loads(row[0])
            for spectrum in CRAFT_SPECTRUMS:
                if spectrum in scores:
                    spectrum_scores[spectrum].append(scores[spectrum])

        trends = []
        for spectrum, scores_list in spectrum_scores.items():
            if len(scores_list) < 2:
                continue
            avg = sum(scores_list) / len(scores_list)

            # Direction: compare first half to second half
            mid = len(scores_list) // 2
            recent_avg = sum(scores_list[:mid]) / mid if mid > 0 else avg
            older_avg = sum(scores_list[mid:]) / (len(scores_list) - mid)
            diff = recent_avg - older_avg

            if diff > 0.1:
                direction = "improving"
            elif diff < -0.1:
                direction = "declining"
            else:
                direction = "stable"

            concern = ""
            if avg < -0.3:
                spec = CRAFT_SPECTRUMS[spectrum]
                concern = f"Consistently {spec['negative']} — needs attention."
            elif direction == "declining" and avg < 0:
                concern = "Declining and below neutral — watch this."

            trends.append(
                CraftTrend(
                    spectrum=spectrum,
                    recent_scores=scores_list,
                    average=round(avg, 3),
                    direction=direction,
                    concern=concern,
                )
            )
        return trends
    finally:
        conn.close()


def get_recent_assessments(n: int = 5) -> list[dict[str, Any]]:
    """Get recent craft assessments."""
    import json

    init_critique_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM craft_assessments ORDER BY assessed_at DESC LIMIT ?",
            (n,),
        ).fetchall()
        return [
            {
                "assessment_id": r[0],
                "session_id": r[1],
                "scores": json.loads(r[2]),
                "overall": r[3],
                "notes": json.loads(r[4]),
                "assessed_at": r[5],
            }
            for r in rows
        ]
    finally:
        conn.close()


# ─── Formatting ──────────────────────────────────────────────────────


def format_craft_assessment(assessment: CraftAssessment) -> str:
    """Format a single craft assessment."""
    lines = ["### Craft Self-Assessment"]
    lines.append(f"  Overall: {assessment.overall:+.2f}")
    for spectrum, score in assessment.scores.items():
        spec = CRAFT_SPECTRUMS.get(spectrum, {})
        label = spec.get("description", spectrum)
        bar = _score_bar(score)
        lines.append(f"  {spectrum}: {bar} ({score:+.2f}) — {label}")
    if assessment.notes:
        for note in assessment.notes:
            lines.append(f"  * {note}")
    return "\n".join(lines)


def format_craft_trends(trends: list[CraftTrend] | None = None) -> str:
    """Format craft trends for display."""
    if trends is None:
        trends = get_craft_trends()
    if not trends:
        return "Not enough assessments for trends yet."

    lines = ["### Craft Trends"]
    for trend in trends:
        arrow = {"improving": "↑", "declining": "↓", "stable": "→"}
        lines.append(
            f"  {trend.spectrum}: {trend.average:+.2f} {arrow.get(trend.direction, '→')} "
            f"({trend.direction})"
        )
        if trend.concern:
            lines.append(f"    [!] {trend.concern}")
    return "\n".join(lines)


def _score_bar(score: float) -> str:
    """Visual bar for -1.0 to 1.0 score."""
    # Map -1..+1 to 0..10
    pos = int((score + 1) * 5)
    pos = max(0, min(10, pos))
    return "▓" * pos + "░" * (10 - pos)
