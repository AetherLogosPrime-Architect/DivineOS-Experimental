"""Session Features — Analysis features that build on raw JSONL session data.

Features:
3. Tone tracking    — Detects when user mood shifts and what the AI did in between
5. Session timeline — Plain-English story of what happened
6. Files touched    — Every file the AI read, edited, or created
8. Work vs talk     — Was the AI doing things or writing paragraphs?
9. Request vs delivery — Did you get what you asked for?
10. Error recovery  — When something broke, what did the AI do next?
7. Cross-session    — Compare patterns across multiple sessions (queries only)

Features 1 (quality checks), 2 (plain English), and 4 (report card) are in quality_checks.py.
Tone tracking (Feature 3) is in tone_tracking.py.
Database setup and storage are in feature_storage.py.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from divineos.analysis.record_extraction import (
    _build_tool_result_map,
    _extract_tool_calls,
    _get_assistant_text,
)
from divineos.analysis.session_analyzer import (
    _extract_user_text,
    _load_records,
)
from divineos.analysis.tone_tracking import (
    ToneShift,
    analyze_tone_shifts,
    tone_report,
)
from divineos.core.fidelity import compute_content_hash


# --- Dataclasses ---


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


from divineos.analysis._session_types import (  # noqa: E402
    ErrorRecoveryEntry,
    TaskTracking,
)
from divineos.analysis.session_features_extra import (  # noqa: E402
    analyze_error_recovery as analyze_error_recovery,
    analyze_request_delivery as analyze_request_delivery,
    error_recovery_report as error_recovery_report,
    get_cross_session_summary as get_cross_session_summary,
)


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
                ),
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
                ),
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
                    ),
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
                    ),
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
                    ),
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
        f"({reads} reads, {edits} edits/writes).",
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
# Full Session Analysis — runs all features
# ============================================================


@dataclass
class FullSessionAnalysis:
    """Complete analysis from all features."""

    session_id: str
    tone_shifts: list[ToneShift] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)
    files_touched: list[FileTouched] = field(default_factory=list)
    activity: ActivityBreakdown | None = None
    task_tracking: TaskTracking | None = None
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
