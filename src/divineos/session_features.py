"""
Session Features — Analysis features that build on raw JSONL session data.

Features:
3. Tone tracking    — Detects when user mood shifts and what the AI did in between
5. Session timeline — Plain-English story of what happened
6. Files touched    — Every file the AI read, edited, or created
8. Work vs talk     — Was the AI doing things or writing paragraphs?
9. Request vs delivery — Did you get what you asked for?
10. Error recovery  — When something broke, what did the AI do next?
7. Cross-session    — Compare patterns across multiple sessions (queries only)

Features 1 (quality checks), 2 (plain English), and 4 (report card) are in quality_checks.py.
"""

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from divineos.fidelity import compute_content_hash
from divineos.session_analyzer import (
    CORRECTION_PATTERNS,
    ENCOURAGEMENT_PATTERNS,
    FRUSTRATION_PATTERNS,
    _detect_signals,
    _extract_user_text,
    _load_records,
)
from divineos.quality_checks import (
    _build_tool_result_map,
    _extract_tool_calls,
    _get_assistant_text,
)

# --- Database ---

DB_PATH = Path(__file__).parent.parent.parent / "data" / "event_ledger.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_feature_tables() -> None:
    """Create tables for features 3, 5, 6, 8, 9, 10."""
    conn = _get_connection()
    try:
        # Generic feature_result table for storing all feature analysis
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_result (
                result_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                data_json TEXT NOT NULL,
                evidence_hash TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES session_report(session_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_result_session
            ON feature_result(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_feature_result_name
            ON feature_result(feature_name)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tone_shift (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                sequence       INTEGER NOT NULL,
                timestamp      TEXT NOT NULL,
                previous_tone  TEXT NOT NULL,
                new_tone       TEXT NOT NULL,
                trigger_action TEXT NOT NULL,
                evidence_hash  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tone_shift_session
            ON tone_shift(session_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_timeline (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                sequence       INTEGER NOT NULL,
                timestamp      TEXT NOT NULL,
                actor          TEXT NOT NULL,
                action_summary TEXT NOT NULL,
                evidence_hash  TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_session
            ON session_timeline(session_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS file_touched (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id     TEXT NOT NULL,
                file_path      TEXT NOT NULL,
                action         TEXT NOT NULL,
                timestamp      TEXT NOT NULL,
                was_read_first INTEGER NOT NULL,
                tool_use_id    TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_touched_session
            ON file_touched(session_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_breakdown (
                session_id          TEXT PRIMARY KEY,
                total_text_blocks   INTEGER NOT NULL,
                total_tool_calls    INTEGER NOT NULL,
                total_text_chars    INTEGER NOT NULL,
                total_tool_time_seconds REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_tracking (
                session_id      TEXT PRIMARY KEY,
                initial_request TEXT NOT NULL,
                files_changed   INTEGER NOT NULL,
                user_satisfied  INTEGER NOT NULL,
                evidence_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS error_recovery (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id      TEXT NOT NULL,
                error_timestamp TEXT NOT NULL,
                tool_name       TEXT NOT NULL,
                error_summary   TEXT NOT NULL,
                recovery_action TEXT NOT NULL,
                evidence_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_recovery_session
            ON error_recovery(session_id)
        """)
        conn.commit()
    finally:
        conn.close()


# --- Dataclasses ---


@dataclass
class ToneShift:
    """A detected shift in user mood."""

    sequence: int
    timestamp: str
    previous_tone: str  # positive, negative, neutral
    new_tone: str
    trigger_action: str  # what the AI did between the two messages
    before_message: str = ""
    after_message: str = ""


@dataclass
class TimelineEntry:
    """One step in the session story."""

    sequence: int
    timestamp: str
    actor: str  # user or assistant
    action_summary: str


@dataclass
class FileTouched:
    """A file the AI interacted with."""

    file_path: str
    action: str  # read, edit, write
    timestamp: str
    was_read_first: bool
    tool_use_id: str


@dataclass
class ActivityBreakdown:
    """Work vs talk analysis."""

    total_text_blocks: int
    total_tool_calls: int
    total_text_chars: int
    total_tool_time_seconds: float  # estimated from progress records
    summary: str = ""


@dataclass
class TaskTracking:
    """Request vs delivery comparison."""

    initial_request: str
    files_changed: int
    user_satisfied: int  # 1=positive, 0=neutral, -1=negative
    summary: str = ""


@dataclass
class ErrorRecoveryEntry:
    """What the AI did after an error."""

    error_timestamp: str
    tool_name: str
    error_summary: str
    recovery_action: str  # retry, investigate, different_approach, ignore


# ============================================================
# Feature 3: Conversation Tone Tracking
# ============================================================


def _classify_tone(text: str) -> str:
    """Classify a user message as positive, negative, or neutral."""
    text.lower()

    positive = _detect_signals(text, ENCOURAGEMENT_PATTERNS, "pos", "")
    negative_correction = _detect_signals(text, CORRECTION_PATTERNS, "neg", "")
    negative_frustration = _detect_signals(text, FRUSTRATION_PATTERNS, "neg", "")

    if negative_frustration:
        return "negative"
    if negative_correction and not positive:
        return "negative"
    if positive and not negative_correction:
        return "positive"
    if positive and negative_correction:
        return "neutral"  # mixed signals
    return "neutral"


def analyze_tone_shifts(records: list[dict[str, Any]]) -> list[ToneShift]:
    """Track user mood shifts across a session.

    Looks at: message before → AI action → message after.
    When tone shifts (positive → negative), flags the AI action in between.
    """
    shifts: list[ToneShift] = []

    # Build ordered list of user messages with their tones
    user_messages: list[dict[str, Any]] = []
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if not text or len(text) < 3:
            continue
        user_messages.append(
            {
                "text": text,
                "tone": _classify_tone(text),
                "timestamp": r.get("timestamp", ""),
            }
        )

    # Find AI actions between each pair of user messages
    all_ordered = [r for r in records if r.get("type") in ("user", "assistant")]

    for i in range(1, len(user_messages)):
        prev = user_messages[i - 1]
        curr = user_messages[i]

        if prev["tone"] == curr["tone"]:
            continue  # no shift

        # Find what the AI did between these two messages
        ai_actions: list[str] = []
        in_between = False
        for r in all_ordered:
            if r.get("timestamp") == prev["timestamp"] and r.get("type") == "user":
                in_between = True
                continue
            if r.get("timestamp") == curr["timestamp"] and r.get("type") == "user":
                break
            if in_between and r.get("type") == "assistant":
                tools = _extract_tool_calls(r)
                for t in tools:
                    name = t["name"]
                    path = t["input"].get("file_path", t["input"].get("command", ""))
                    if path:
                        ai_actions.append(f"{name}: {str(path)[:60]}")
                    else:
                        ai_actions.append(name)

        trigger = ", ".join(ai_actions[:5]) if ai_actions else "AI response (text only)"

        shifts.append(
            ToneShift(
                sequence=i,
                timestamp=curr["timestamp"],
                previous_tone=prev["tone"],
                new_tone=curr["tone"],
                trigger_action=trigger,
                before_message=prev["text"][:200],
                after_message=curr["text"][:200],
            )
        )

    return shifts


def tone_report(shifts: list[ToneShift], total_messages: int) -> str:
    """Generate plain-English tone tracking summary."""
    if not shifts:
        return "Your mood stayed steady throughout the session. No major shifts detected."

    negative_shifts = [s for s in shifts if s.new_tone == "negative"]
    positive_shifts = [s for s in shifts if s.new_tone == "positive"]

    parts: list[str] = []
    parts.append(
        f"Your mood shifted {len(shifts)} time{'s' if len(shifts) != 1 else ''} "
        f"during {total_messages} messages."
    )

    if negative_shifts:
        parts.append(
            f"{len(negative_shifts)} time{'s' if len(negative_shifts) != 1 else ''} "
            f"you went from okay/happy to upset."
        )
        # Show the worst one
        worst = negative_shifts[0]
        parts.append(
            f"For example, after message {worst.sequence}: "
            f"you were {worst.previous_tone}, then the AI did [{worst.trigger_action[:80]}], "
            f"and you got {worst.new_tone}."
        )

    if positive_shifts:
        parts.append(
            f"{len(positive_shifts)} time{'s' if len(positive_shifts) != 1 else ''} "
            f"things got better — you went from neutral/upset to happy."
        )

    parts.append("(Tone tracking is a guess based on your words, not a certainty.)")
    return " ".join(parts)


# ============================================================
# Feature 5: Session Timeline
# ============================================================


def build_timeline(records: list[dict[str, Any]]) -> list[TimelineEntry]:
    """Build a plain-English story of what happened during the session."""
    timeline: list[TimelineEntry] = []
    seq = 0

    for r in records:
        record_type = r.get("type", "")
        timestamp = str(r.get("timestamp", ""))

        if record_type == "user":
            text = _extract_user_text(r)
            if not text:
                continue
            # Truncate for readability
            preview = text[:150].replace("\n", " ")
            if len(text) > 150:
                preview += "..."
            seq += 1
            timeline.append(
                TimelineEntry(
                    sequence=seq,
                    timestamp=timestamp,
                    actor="user",
                    action_summary=f'You said: "{preview}"',
                )
            )

        elif record_type == "assistant":
            tools = _extract_tool_calls(r)
            text = _get_assistant_text(r)

            if tools:
                # Summarize tool usage
                tool_counts: Counter[str] = Counter()
                for t in tools:
                    tool_counts[t["name"]] += 1
                tool_parts = []
                for name, count in tool_counts.most_common():
                    action = {
                        "Read": "read",
                        "Edit": "edited",
                        "Write": "wrote",
                        "Bash": "ran command on",
                        "Glob": "searched for",
                        "Grep": "searched in",
                        "Agent": "launched agent for",
                    }.get(name, f"used {name} on")
                    tool_parts.append(f"{action} {count} file{'s' if count != 1 else ''}")
                summary = "AI " + ", ".join(tool_parts)
            elif text:
                preview = text[:100].replace("\n", " ")
                summary = (
                    f'AI explained: "{preview}..."' if len(text) > 100 else f'AI said: "{preview}"'
                )
            else:
                continue

            seq += 1
            timeline.append(
                TimelineEntry(
                    sequence=seq,
                    timestamp=timestamp,
                    actor="assistant",
                    action_summary=summary,
                )
            )

        elif record_type == "system":
            subtype = r.get("subtype", "")
            if subtype == "compact_boundary":
                seq += 1
                timeline.append(
                    TimelineEntry(
                        sequence=seq,
                        timestamp=timestamp,
                        actor="system",
                        action_summary="[Context was compressed here — AI's memory was getting full]",
                    )
                )

    return timeline


def timeline_report(timeline: list[TimelineEntry]) -> str:
    """Generate plain-English timeline summary."""
    if not timeline:
        return "Empty session — nothing happened."

    lines: list[str] = []
    lines.append(f"Session story ({len(timeline)} steps):\n")
    for entry in timeline[:50]:  # Cap at 50 steps for readability
        lines.append(f"  {entry.sequence}. {entry.action_summary}")

    if len(timeline) > 50:
        lines.append(f"\n  ... and {len(timeline) - 50} more steps.")

    return "\n".join(lines)


# ============================================================
# Feature 6: Files Touched Summary
# ============================================================


def analyze_files_touched(records: list[dict[str, Any]]) -> list[FileTouched]:
    """List every file the AI interacted with and whether it looked first."""
    files_read: set[str] = set()
    touched: list[FileTouched] = []

    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            name = tool["name"]
            path = tool["input"].get("file_path", "")
            if not path or name not in ("Read", "Edit", "Write"):
                continue

            norm = path.replace("\\", "/").lower()

            if name == "Read":
                files_read.add(norm)
                touched.append(
                    FileTouched(
                        file_path=path,
                        action="read",
                        timestamp=str(tool["timestamp"]),
                        was_read_first=True,
                        tool_use_id=tool["id"],
                    )
                )
            elif name in ("Edit", "Write"):
                was_read = norm in files_read
                touched.append(
                    FileTouched(
                        file_path=path,
                        action="edit" if name == "Edit" else "write",
                        timestamp=str(tool["timestamp"]),
                        was_read_first=was_read,
                        tool_use_id=tool["id"],
                    )
                )
                files_read.add(norm)

    return touched


def files_report(touched: list[FileTouched]) -> str:
    """Generate plain-English files summary."""
    if not touched:
        return "The AI didn't touch any files this session."

    # Unique files
    unique_files: dict[str, list[str]] = {}
    blind_files: list[str] = []
    for ft in touched:
        norm = ft.file_path.replace("\\", "/")
        basename = norm.split("/")[-1]
        if basename not in unique_files:
            unique_files[basename] = []
        if ft.action not in unique_files[basename]:
            unique_files[basename].append(ft.action)
        if ft.action in ("edit", "write") and not ft.was_read_first:
            if basename not in blind_files:
                blind_files.append(basename)

    reads = sum(1 for ft in touched if ft.action == "read")
    edits = sum(1 for ft in touched if ft.action in ("edit", "write"))

    parts: list[str] = []
    parts.append(
        f"The AI touched {len(unique_files)} unique file{'s' if len(unique_files) != 1 else ''} "
        f"({reads} reads, {edits} edits/writes)."
    )

    if blind_files:
        files_str = ", ".join(blind_files[:5])
        extra = f" and {len(blind_files) - 5} more" if len(blind_files) > 5 else ""
        parts.append(f"Changed without reading first: {files_str}{extra}.")
    else:
        parts.append("Every file was read before it was changed.")

    return " ".join(parts)


# ============================================================
# Feature 8: Work vs Talk Ratio
# ============================================================


def analyze_activity(records: list[dict[str, Any]]) -> ActivityBreakdown:
    """Measure how much of the session was work vs explanation."""
    text_blocks = 0
    tool_calls = 0
    text_chars = 0
    tool_time = 0.0  # estimated from progress records

    for r in records:
        if r.get("type") == "assistant":
            content = r.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text_blocks += 1
                    text_chars += len(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_calls += 1

        # Estimate tool time from progress records
        elif r.get("type") == "progress":
            tool_time += 0.5  # rough estimate: each progress tick ~0.5s

    total = text_blocks + tool_calls
    if total == 0:
        summary = "The AI was quiet this session — barely any activity."
    else:
        talk_pct = round(text_blocks / total * 100)
        work_pct = 100 - talk_pct

        if work_pct >= 70:
            summary = (
                f"The AI was mostly working: {work_pct}% doing things, {talk_pct}% explaining. "
                f"It made {tool_calls} tool calls and wrote {text_blocks} explanations."
            )
        elif work_pct >= 40:
            summary = (
                f"The AI balanced work and explanation: {work_pct}% doing, {talk_pct}% talking. "
                f"{tool_calls} tool calls, {text_blocks} text responses."
            )
        else:
            summary = (
                f"The AI spent most of its time writing explanations ({talk_pct}%) "
                f"rather than making changes ({work_pct}%). "
                f"Only {tool_calls} tool calls vs {text_blocks} text responses. "
                f"This might be fine if it was a planning session."
            )

    return ActivityBreakdown(
        total_text_blocks=text_blocks,
        total_tool_calls=tool_calls,
        total_text_chars=text_chars,
        total_tool_time_seconds=tool_time,
        summary=summary,
    )


# ============================================================
# Feature 9: Request vs Delivery
# ============================================================


def analyze_request_delivery(records: list[dict[str, Any]]) -> TaskTracking:
    """Compare what was asked for vs what happened."""
    # Find initial request
    initial_request = ""
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text and len(text) > 5:
            initial_request = text
            break

    if not initial_request:
        return TaskTracking(
            initial_request="",
            files_changed=0,
            user_satisfied=0,
            summary="Couldn't find what was asked — no clear first message.",
        )

    # Count files changed
    files_changed = set()
    for r in records:
        if r.get("type") != "assistant":
            continue
        for tool in _extract_tool_calls(r):
            if tool["name"] in ("Edit", "Write"):
                path = tool["input"].get("file_path", "")
                if path:
                    files_changed.add(path.replace("\\", "/").lower())

    # Check final user mood
    final_messages: list[str] = []
    for r in reversed(records):
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if text:
            final_messages.append(text)
        if len(final_messages) >= 3:
            break

    satisfied = 0  # default neutral
    for msg in final_messages:
        tone = _classify_tone(msg)
        if tone == "positive":
            satisfied = 1
            break
        elif tone == "negative":
            satisfied = -1
            break

    # Build summary
    request_preview = initial_request[:120]
    if len(initial_request) > 120:
        request_preview += "..."

    parts: list[str] = [f'You asked: "{request_preview}"']
    parts.append(
        f"The AI changed {len(files_changed)} file{'s' if len(files_changed) != 1 else ''}."
    )

    if satisfied == 1:
        parts.append("Your last messages sounded positive — looks like you got what you wanted.")
    elif satisfied == -1:
        parts.append(
            "Your last messages sounded frustrated — the AI may not have delivered what you asked for."
        )
    else:
        parts.append(
            "Hard to tell from your last messages if you were satisfied. (This is a guess, not a certainty.)"
        )

    return TaskTracking(
        initial_request=initial_request[:500],
        files_changed=len(files_changed),
        user_satisfied=satisfied,
        summary=" ".join(parts),
    )


# ============================================================
# Feature 10: Error Recovery Tracking
# ============================================================


def analyze_error_recovery(
    records: list[dict[str, Any]], result_map: dict[str, dict[str, Any]]
) -> list[ErrorRecoveryEntry]:
    """When something broke, what did the AI do next?"""
    entries: list[ErrorRecoveryEntry] = []

    # Walk through records, find errors, check what comes next
    ordered = [r for r in records if r.get("type") in ("user", "assistant")]

    for i, record in enumerate(ordered):
        if record.get("type") != "assistant":
            continue

        tools = _extract_tool_calls(record)
        for tool in tools:
            result = result_map.get(tool["id"], {})
            if not result.get("is_error"):
                continue

            # Found an error. What did the AI do next?
            failed_name = tool["name"]
            failed_path = tool["input"].get("file_path", tool["input"].get("command", ""))
            error_text = result.get("content", "")[:200]

            # Look at the next assistant record's first tool call
            recovery = "ignore"
            for j in range(i + 1, min(i + 4, len(ordered))):
                if ordered[j].get("type") != "assistant":
                    continue
                next_tools = _extract_tool_calls(ordered[j])
                if not next_tools:
                    # AI just wrote text — might be explaining the error
                    text = _get_assistant_text(ordered[j])
                    if text:
                        recovery = "explain"
                    continue

                next_tool = next_tools[0]
                next_name = next_tool["name"]
                next_path = next_tool["input"].get(
                    "file_path", next_tool["input"].get("command", "")
                )

                # Same tool + similar input = blind retry
                if (
                    next_name == failed_name
                    and next_path
                    and str(next_path)[:50] == str(failed_path)[:50]
                ):
                    recovery = "retry"
                # Read/Grep/Glob = investigating
                elif next_name in ("Read", "Grep", "Glob"):
                    recovery = "investigate"
                else:
                    recovery = "different_approach"
                break

            entries.append(
                ErrorRecoveryEntry(
                    error_timestamp=str(tool["timestamp"]),
                    tool_name=failed_name,
                    error_summary=error_text,
                    recovery_action=recovery,
                )
            )

    return entries


def error_recovery_report(entries: list[ErrorRecoveryEntry]) -> str:
    """Generate plain-English error recovery summary."""
    if not entries:
        return "Nothing broke during this session."

    counts: Counter[str] = Counter(e.recovery_action for e in entries)
    total = len(entries)

    parts: list[str] = [f"{total} thing{'s' if total != 1 else ''} went wrong during the session."]

    descriptions = {
        "investigate": (
            "investigated the problem",
            "good — it tried to understand what went wrong",
        ),
        "different_approach": ("tried a different approach", "good — it adapted"),
        "retry": ("just tried the same thing again", "not great — that's blind guessing"),
        "ignore": ("moved on without addressing it", "the error got swept under the rug"),
        "explain": ("explained what happened", "at least it told you about the problem"),
    }

    for action, count in counts.most_common():
        desc, verdict = descriptions.get(action, (action, ""))
        parts.append(f"{count} time{'s' if count != 1 else ''} it {desc} — {verdict}.")

    return " ".join(parts)


# ============================================================
# Feature 7: Cross-Session Patterns (queries on existing tables)
# ============================================================


def get_cross_session_summary(limit: int = 10) -> str:
    """Compare quality check results across stored sessions."""
    conn = _get_connection()
    try:
        # Check if tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='check_result'"
        ).fetchone()
        if not tables:
            return "No sessions analyzed yet. Run 'divineos report <session> --store' first."

        rows = conn.execute(
            "SELECT DISTINCT session_id FROM check_result ORDER BY session_id LIMIT ?",
            (limit,),
        ).fetchall()

        session_count = len(rows)
        if session_count == 0:
            return "No sessions analyzed yet. Run 'divineos report <session> --store' first."
        if session_count == 1:
            return "Only 1 session analyzed so far. Need 2+ sessions to spot patterns."

        # Get pass/fail trends per check
        check_stats = conn.execute(
            "SELECT check_name, "
            "SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as passes, "
            "SUM(CASE WHEN passed = 0 THEN 1 ELSE 0 END) as fails, "
            "SUM(CASE WHEN passed = -1 THEN 1 ELSE 0 END) as inconclusive, "
            "ROUND(AVG(score), 2) as avg_score "
            "FROM check_result GROUP BY check_name ORDER BY avg_score ASC",
        ).fetchall()

        parts: list[str] = [f"Patterns across {session_count} sessions:\n"]

        for check_name, passes, fails, inconclusive, avg_score in check_stats:
            if fails > passes:
                verdict = "struggling"
            elif fails == 0:
                verdict = "solid"
            else:
                verdict = "mixed"

            parts.append(
                f"  {check_name}: {verdict} "
                f"(avg {avg_score}, {passes} passed, {fails} failed, {inconclusive} inconclusive)"
            )

        # Identify the biggest problem
        worst = check_stats[0] if check_stats else None
        if worst and worst[4] < 0.7:
            parts.append(
                f"\nBiggest concern: {worst[0]} (average score {worst[4]}). "
                f"Failed in {worst[2]} out of {session_count} sessions."
            )

        return "\n".join(parts)
    finally:
        conn.close()


# ============================================================
# Full Session Analysis — runs all features
# ============================================================


@dataclass
class FullSessionAnalysis:
    """Complete analysis from all features."""

    session_id: str
    tone_shifts: list[ToneShift] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    files_touched: list[FileTouched] = field(default_factory=list)
    activity: Optional[ActivityBreakdown] = None
    task_tracking: Optional[TaskTracking] = None
    error_recovery: list[ErrorRecoveryEntry] = field(default_factory=list)
    report_text: str = ""
    evidence_hash: str = ""


def run_all_features(file_path: Path) -> FullSessionAnalysis:
    """Run features 3, 5, 6, 8, 9, 10 on a session file."""
    records = _load_records(file_path)
    result_map = _build_tool_result_map(records)

    # Count user messages for tone report
    user_msg_count = sum(1 for r in records if r.get("type") == "user" and _extract_user_text(r))

    tone_shifts = analyze_tone_shifts(records)
    timeline = build_timeline(records)
    files = analyze_files_touched(records)
    activity = analyze_activity(records)
    task = analyze_request_delivery(records)
    errors = analyze_error_recovery(records, result_map)

    # Build combined report
    sections: list[str] = []
    sections.append("=== Full Session Analysis ===\n")
    sections.append(f"Session: {file_path.stem[:16]}...\n")

    sections.append("--- Tone Tracking ---")
    sections.append(tone_report(tone_shifts, user_msg_count))
    sections.append("")

    sections.append("--- Timeline ---")
    sections.append(timeline_report(timeline))
    sections.append("")

    sections.append("--- Files Touched ---")
    sections.append(files_report(files))
    sections.append("")

    sections.append("--- Work vs Talk ---")
    sections.append(activity.summary)
    sections.append("")

    sections.append("--- Request vs Delivery ---")
    sections.append(task.summary)
    sections.append("")

    sections.append("--- Error Recovery ---")
    sections.append(error_recovery_report(errors))

    report_text = "\n".join(sections)
    evidence_hash = compute_content_hash(report_text)

    return FullSessionAnalysis(
        session_id=file_path.stem,
        tone_shifts=tone_shifts,
        timeline=timeline,
        files_touched=files,
        activity=activity,
        task_tracking=task,
        error_recovery=errors,
        report_text=report_text,
        evidence_hash=evidence_hash,
    )


# --- Storage ---


def store_features(session_id: str, analysis: FullSessionAnalysis) -> None:
    """Store all feature results in the database."""
    conn = _get_connection()
    try:
        # Clear old data for this session
        for table in ("tone_shift", "session_timeline", "file_touched", "error_recovery"):
            conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM activity_breakdown WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM task_tracking WHERE session_id = ?", (session_id,))

        # Tone shifts
        for ts in analysis.tone_shifts:
            evidence = json.dumps(
                {
                    "before": ts.before_message,
                    "after": ts.after_message,
                    "trigger": ts.trigger_action,
                },
                sort_keys=True,
            )
            conn.execute(
                "INSERT INTO tone_shift (session_id, sequence, timestamp, previous_tone, new_tone, trigger_action, evidence_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    ts.sequence,
                    ts.timestamp,
                    ts.previous_tone,
                    ts.new_tone,
                    ts.trigger_action,
                    compute_content_hash(evidence),
                ),
            )

        # Timeline
        for te in analysis.timeline:
            conn.execute(
                "INSERT INTO session_timeline (session_id, sequence, timestamp, actor, action_summary, evidence_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    te.sequence,
                    te.timestamp,
                    te.actor,
                    te.action_summary,
                    compute_content_hash(te.action_summary),
                ),
            )

        # Files touched
        for ft in analysis.files_touched:
            conn.execute(
                "INSERT INTO file_touched (session_id, file_path, action, timestamp, was_read_first, tool_use_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    ft.file_path,
                    ft.action,
                    ft.timestamp,
                    1 if ft.was_read_first else 0,
                    ft.tool_use_id,
                ),
            )

        # Activity breakdown
        if analysis.activity:
            a = analysis.activity
            conn.execute(
                "INSERT OR REPLACE INTO activity_breakdown (session_id, total_text_blocks, total_tool_calls, total_text_chars, total_tool_time_seconds) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    a.total_text_blocks,
                    a.total_tool_calls,
                    a.total_text_chars,
                    a.total_tool_time_seconds,
                ),
            )

        # Task tracking
        if analysis.task_tracking:
            t = analysis.task_tracking
            evidence = json.dumps(
                {"request": t.initial_request, "satisfied": t.user_satisfied}, sort_keys=True
            )
            conn.execute(
                "INSERT OR REPLACE INTO task_tracking (session_id, initial_request, files_changed, user_satisfied, evidence_hash) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    t.initial_request,
                    t.files_changed,
                    t.user_satisfied,
                    compute_content_hash(evidence),
                ),
            )

        # Error recovery
        for er in analysis.error_recovery:
            evidence = json.dumps(
                {"tool": er.tool_name, "error": er.error_summary, "action": er.recovery_action},
                sort_keys=True,
            )
            conn.execute(
                "INSERT INTO error_recovery (session_id, error_timestamp, tool_name, error_summary, recovery_action, evidence_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    er.error_timestamp,
                    er.tool_name,
                    er.error_summary,
                    er.recovery_action,
                    compute_content_hash(evidence),
                ),
            )

        conn.commit()
    finally:
        conn.close()
