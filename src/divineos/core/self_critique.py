"""Self-Critique — periodic self-assessment of craft quality.

Goes beyond quality checks (which measure outcomes) to assess the
quality of reasoning, decision-making, and execution craft. Tracks
multiple "craft spectrums" over time to reveal patterns in how well
I'm thinking, not just what I'm producing.

The difference: quality checks ask "did the code work?" Self-critique
asks "was my approach to the problem elegant or brute-force?"

Runs automatically during extraction (formerly SESSION_END), not on demand. The point is to
build a habit of reflection without being asked.

Sanskrit anchor: atma-pariksha (self-examination, introspective assessment).
"""

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from divineos.core.knowledge import _get_connection

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
    scores: dict[str, float]  # spectrum_name -> score (-1.0 to 1.0)
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


def assess_session_craft(session_id: str = "", analysis: Any = None) -> CraftAssessment:
    """Run automatic self-critique for the current session.

    Computes craft scores from measurable session data:
    - Elegance: ratio of files read to files edited (more reading = more care)
    - Thoroughness: test count relative to code changes
    - Autonomy: OS consultation frequency (used the OS without being forced)
    - Proportionality: lines changed relative to problem size
    - Communication: corrections received (fewer = clearer communication)

    If analysis (SessionAnalysis) is provided, uses its richer data (tool_usage,
    corrections, encouragements) instead of scanning the event ledger. The ledger
    only has DivineOS internal tool calls; the analysis has Claude Code's actual
    Read/Edit/Bash/Grep calls from the JSONL transcript.
    """

    init_critique_table()
    scores: dict[str, float] = {}
    notes: list[str] = []

    # Gather evidence — prefer analysis object (rich) over ledger scan (sparse)
    evidence = _gather_session_evidence(analysis=analysis)

    # Elegance: did changes land cleanly, or require rework?
    # Rework = re-editing the same file multiple times. Low rework = elegant.
    edits = evidence.get("file_edits", 0)
    rework = evidence.get("rework_edits", 0)
    hook_failures = evidence.get("hook_failures", 0)
    if edits > 0:
        clean_ratio = 1.0 - (rework / edits)  # 1.0 = no rework, 0.0 = all rework
        hook_penalty = min(0.4, hook_failures * 0.2)  # pre-commit failures hurt
        scores["elegance"] = min(1.0, max(-1.0, (clean_ratio - 0.5) * 2 - hook_penalty))
    else:
        scores["elegance"] = 0.0

    # Thoroughness: did tests run AND pass?
    tests_run = evidence.get("tests_run", 0)
    tests_failed = evidence.get("tests_failed", 0)
    if edits > 0 and tests_run > 0:
        # Tests run relative to changes (did you test?) + pass rate (did they pass?)
        ran_tests = min(1.0, tests_run / max(edits, 1))
        pass_rate = 1.0 - (tests_failed / tests_run) if tests_run > 0 else 0.0
        scores["thoroughness"] = min(1.0, max(-1.0, (ran_tests * 0.5 + pass_rate * 0.5 - 0.3) * 2))
    elif edits > 0:
        scores["thoroughness"] = -0.5  # edited code but never ran tests
        notes.append("No tests run after code changes.")
    else:
        scores["thoroughness"] = 0.0

    # Autonomy: voluntary OS use vs forced gate blocks
    os_queries = evidence.get("os_queries", 0)
    gate_blocks = evidence.get("gate_blocks", 0)
    if gate_blocks > 0:
        scores["autonomy"] = max(-1.0, -0.3 * gate_blocks)
        notes.append(f"Gate blocked {gate_blocks} time(s) — hooks had to force compliance.")
    elif os_queries > 0:
        scores["autonomy"] = min(1.0, os_queries * 0.2)
    else:
        scores["autonomy"] = 0.0

    # Proportionality: files changed relative to user messages
    # Many files for a simple request = over-engineering
    user_msgs = evidence.get("user_messages", 0)
    unique_files = evidence.get("unique_files_edited", 0)
    if user_msgs > 0 and unique_files > 0:
        scope_ratio = unique_files / max(user_msgs, 1)
        # 1-3 files per message = good, 10+ = probably over-engineering
        if scope_ratio <= 3:
            scores["proportionality"] = min(1.0, 0.5)
        elif scope_ratio <= 6:
            scores["proportionality"] = 0.0
        else:
            scores["proportionality"] = max(-1.0, -0.3 * (scope_ratio - 6) / 4)
            notes.append(f"Touched {unique_files} files for {user_msgs} user message(s).")
    else:
        scores["proportionality"] = 0.0

    # Communication: user feedback ratio (corrections vs encouragements)
    corrections = evidence.get("corrections", 0)
    encouragements = evidence.get("encouragements", 0)
    if corrections + encouragements > 0:
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


def _gather_session_evidence(analysis: Any = None) -> dict[str, int]:
    """Gather measurable evidence from the current session.

    If a SessionAnalysis object is provided, extracts evidence from its rich
    tool_usage data (which comes from the JSONL transcript and includes Claude
    Code's own Read/Edit/Bash/Grep calls). Falls back to scanning the event
    ledger, which only has DivineOS internal tool calls.

    Tracks real outcomes, not just activity counts:
    - rework_edits: same file edited multiple times (indicates iteration)
    - hook_failures: pre-commit hook rejections (indicates sloppy staging)
    - tests_failed: test runs that failed (vs passed)
    - unique_files_edited: scope of changes
    - user_messages: how many user turns (for proportionality)
    """
    evidence: dict[str, int] = {
        "file_reads": 0,
        "file_edits": 0,
        "rework_edits": 0,
        "tests_run": 0,
        "tests_failed": 0,
        "os_queries": 0,
        "gate_blocks": 0,
        "hook_failures": 0,
        "corrections": 0,
        "encouragements": 0,
        "user_messages": 0,
        "unique_files_edited": 0,
    }

    # Prefer analysis object — it has Claude Code's actual tool usage from the
    # JSONL transcript, which the event ledger doesn't capture.
    if analysis is not None:
        try:
            tool_usage = getattr(analysis, "tool_usage", {}) or {}
            evidence["file_reads"] = tool_usage.get("Read", 0) + tool_usage.get("read", 0)
            evidence["file_edits"] = (
                tool_usage.get("Edit", 0)
                + tool_usage.get("edit", 0)
                + tool_usage.get("Write", 0)
                + tool_usage.get("write", 0)
            )
            evidence["tests_run"] = tool_usage.get("Bash", 0) + tool_usage.get("bash", 0)
            evidence["user_messages"] = getattr(analysis, "user_messages", 0)
            evidence["corrections"] = len(getattr(analysis, "corrections", []))
            evidence["encouragements"] = len(getattr(analysis, "encouragements", []))
            evidence["os_queries"] = tool_usage.get("divineos", 0)
            # tool_calls_total gives unique_files_edited a rough proxy
            total_tools = getattr(analysis, "tool_calls_total", 0)
            if total_tools > 0 and evidence["file_edits"] > 0:
                evidence["unique_files_edited"] = max(1, evidence["file_edits"] // 2)
            return evidence
        except _SC_ERRORS:
            pass  # Fall through to ledger scan

    try:
        conn = _get_connection()
        try:
            cutoff = time.time() - 7200
            rows = conn.execute(
                "SELECT event_type, payload FROM system_events "
                "WHERE timestamp > ? ORDER BY timestamp DESC",
                (cutoff,),
            ).fetchall()

            edited_files: set[str] = set()
            edit_counts: dict[str, int] = {}

            for event_type, content in rows:
                content_str = content or ""
                content_lower = content_str.lower()

                if event_type == "TOOL_CALL":
                    # Parse tool_name from JSON payload when available
                    tool_name = ""
                    tool_input: dict[str, Any] = {}
                    try:
                        payload = json.loads(content_str)
                        tool_name = (payload.get("tool_name", "") or "").lower()
                        tool_input = payload.get("tool_input", {}) or {}
                    except (json.JSONDecodeError, AttributeError):
                        pass

                    # Match on parsed tool_name first, fall back to content search
                    if tool_name in ("read", "read_file") or (
                        not tool_name and "read" in content_lower
                    ):
                        evidence["file_reads"] += 1
                    elif tool_name in ("edit", "edit_file", "write", "write_file") or (
                        not tool_name and "edit" in content_lower
                    ):
                        evidence["file_edits"] += 1
                        # Track which files for rework detection
                        file_path = (
                            tool_input.get("file_path", "") or tool_input.get("path", "")
                        ).lower()
                        if not file_path:
                            for word in content_lower.split():
                                if ("/" in word or "\\" in word) and "." in word.split("/")[-1]:
                                    file_path = word
                                    break
                        if file_path:
                            edit_counts[file_path] = edit_counts.get(file_path, 0) + 1
                            edited_files.add(file_path)

                    if "pytest" in content_lower or tool_name in ("run_tests",):
                        evidence["tests_run"] += 1
                    if ("fail" in content_lower or "error" in content_lower) and (
                        "pytest" in content_lower
                    ):
                        evidence["tests_failed"] += 1

                elif event_type == "TOOL_RESULT":
                    # Hook failures: pre-commit hook rejections (specific patterns)
                    if "pre-commit" in content_lower and (
                        "failed" in content_lower or "blocked" in content_lower
                    ):
                        evidence["hook_failures"] += 1
                    # Test failures in results
                    if "failed" in content_lower and "passed" in content_lower:
                        evidence["tests_failed"] += 1
                elif event_type == "OS_QUERY":
                    evidence["os_queries"] += 1
                elif event_type == "USER_INPUT":
                    evidence["user_messages"] += 1

            # Rework = files edited more than once
            evidence["rework_edits"] = sum(count - 1 for count in edit_counts.values() if count > 1)
            evidence["unique_files_edited"] = len(edited_files)

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
        arrow = {"improving": "^", "declining": "v", "stable": "->"}
        lines.append(
            f"  {trend.spectrum}: {trend.average:+.2f} {arrow.get(trend.direction, '->')} "
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
