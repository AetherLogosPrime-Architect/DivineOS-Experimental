"""Session Analyzer — extract meaning from Claude Code JSONL sessions."""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# --- Patterns for detecting user intent ---

CORRECTION_PATTERNS: tuple[str, ...] = (
    r"^no[\s,.]",  # "no" at start of message = rejection
    r"\bwrong\b",
    r"\bthat'?s not\b",
    r"\bdon'?t (?:do|use|add|make|change|remove|delete|mock|skip|edit|write|create|run)\b",
    r"\byou missed\b",
    r"\bnot what i\b",
    r"\bwhy did you\b",
    r"\bwhy were they\b",
    r"\byou only\b",
    r"\bthat doesn'?t\b",
    r"\bthis is wrong\b",
    r"\bactually[,] (?:i|you|we|it|the)\b",
    r"\binstead (?:of that|do|use)\b",
    r"\bstop (?:doing|using|adding|that)\b",
    r"\bplease don'?t\b",
    r"\bi (?:said|asked|meant|wanted)\b",
)

ENCOURAGEMENT_PATTERNS: tuple[str, ...] = (
    r"\bperfect\b",
    r"\bwonderful\b",
    r"\bexcellent\b",
    r"\bamazing\b",
    r"\bproud\b",
    r"\bfantastic\b",
    r"\bgreat job\b",
    r"\bwell done\b",
    r"\bthis is it\b",
    r"\byes!\b",
    r"\blets go\b",
    r"\blet'?s go\b",
    r"\bbeautiful\b",
    r"\bbrilliant\b",
    r"\bi can feel\b",
    r"\bimpressive\b",
)

DECISION_PATTERNS: tuple[str, ...] = (
    r"\blets use\b",
    r"\blet'?s use\b",
    r"\bi'?ll go with\b",
    r"\boption [a-d]\b",
    r"\byes lets\b",
    r"\byes let'?s\b",
    r"\bwe should\b",
    r"\bwe need\b",
    r"\bthe point is\b",
    r"\bthe whole point\b",
)

FRUSTRATION_PATTERNS: tuple[str, ...] = (
    r"\bsigh\b",
    r"\blol\b.*\?",
    r"\bdid you not\b",
    r"\bi already\b",
    r"\bwhat do any\b",
    r"\bthat'?s why\b",
    r"\bi told you\b",
)

PREFERENCE_PATTERNS: tuple[str, ...] = (
    r"\bi prefer\b",
    r"\bi like (?:it )?when\b",
    r"\balways (\w+)",
    r"\bnever (\w+)",
    r"\bmake sure (?:to |you )\b",
    r"\bexplain.+?(?:like|as if)\b",
    r"\bkeep it\b",
    r"\bplain english\b",
    r"\bno jargon\b",
    r"\bbreak it down\b",
    r"\bdon'?t.+?jargon\b",
    r"\blike i'?m (?:dumb|stupid|5|five|new)\b",
    r"\bsimple\b.*\bplease\b",
)


@dataclass
class UserSignal:
    """A detected signal in a user message."""

    signal_type: str  # correction, encouragement, decision, frustration, instruction
    content: str
    timestamp: str
    patterns_matched: list[str] = field(default_factory=list)


@dataclass
class ToolCall:
    """A tool invocation by the assistant."""

    tool_name: str
    timestamp: str
    input_summary: str = ""


@dataclass
class ContextOverflow:
    """A point where the session hit context limits."""

    timestamp: str
    message_index: int
    continuation_text: str = ""


@dataclass
class TopicSegment:
    """A segment of conversation about a particular topic."""

    topic: str
    start_index: int
    end_index: int
    message_count: int
    user_messages: int
    tool_calls: int


@dataclass
class SessionAnalysis:
    """Complete analysis of a single session."""

    source_file: str
    session_id: str

    # Timeline
    start_time: str | None = None
    end_time: str | None = None
    duration_seconds: float = 0.0

    # Counts
    total_records: int = 0
    user_messages: int = 0
    assistant_messages: int = 0
    tool_calls_total: int = 0

    # Model info
    models_used: dict[str, int] = field(default_factory=dict)

    # Detected signals
    corrections: list[UserSignal] = field(default_factory=list)
    encouragements: list[UserSignal] = field(default_factory=list)
    decisions: list[UserSignal] = field(default_factory=list)
    frustrations: list[UserSignal] = field(default_factory=list)
    preferences: list[UserSignal] = field(default_factory=list)

    # Tool patterns
    tool_usage: dict[str, int] = field(default_factory=dict)
    tool_sequence: list[ToolCall] = field(default_factory=list)

    # Context overflows
    context_overflows: list[ContextOverflow] = field(default_factory=list)

    # Conversation flow
    user_message_texts: list[str] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = []
        lines.append(f"=== Session Analysis: {self.session_id[:12]}... ===\n")

        # Timeline
        if self.start_time:
            lines.append(f"  Start:    {self.start_time}")
        if self.end_time:
            lines.append(f"  End:      {self.end_time}")
        if self.duration_seconds > 0:
            hours = self.duration_seconds / 3600
            lines.append(f"  Duration: {hours:.1f} hours")

        lines.append("")

        # Counts
        lines.append(f"  Records:       {self.total_records}")
        lines.append(f"  User msgs:     {self.user_messages}")
        lines.append(f"  Assistant msgs:{self.assistant_messages}")
        lines.append(f"  Tool calls:    {self.tool_calls_total}")
        lines.append(f"  Overflows:     {len(self.context_overflows)}")
        lines.append("")

        # Models
        if self.models_used:
            lines.append("  Models:")
            for model, count in sorted(self.models_used.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"    {model}: {count}")
            lines.append("")

        # Signals
        lines.append(f"  Corrections:    {len(self.corrections)}  (user redirected AI)")
        lines.append(f"  Encouragements: {len(self.encouragements)}  (AI did well)")
        lines.append(f"  Decisions:      {len(self.decisions)}  (user chose direction)")
        lines.append(f"  Frustrations:   {len(self.frustrations)}  (user got impatient)")
        lines.append(f"  Preferences:    {len(self.preferences)}  (user stated preference)")
        lines.append("")

        # Top tools
        if self.tool_usage:
            lines.append("  Top tools:")
            sorted_tools = sorted(self.tool_usage.items(), key=lambda x: x[1], reverse=True)
            for name, count in sorted_tools[:10]:
                bar = "#" * min(count, 40)
                lines.append(f"    {name:20s} {count:4d} {bar}")
            lines.append("")

        # Correction details
        if self.corrections:
            lines.append("  --- Corrections ---")
            for c in self.corrections:
                preview = c.content.replace("\n", " ")[:120]
                lines.append(f"    > {preview}")
            lines.append("")

        # Encouragement details
        if self.encouragements:
            lines.append("  --- Encouragements ---")
            for e in self.encouragements:
                preview = e.content.replace("\n", " ")[:120]
                lines.append(f"    > {preview}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Convert to serializable dict."""
        return {
            "source_file": self.source_file,
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "total_records": self.total_records,
            "user_messages": self.user_messages,
            "assistant_messages": self.assistant_messages,
            "tool_calls_total": self.tool_calls_total,
            "models_used": self.models_used,
            "corrections": len(self.corrections),
            "encouragements": len(self.encouragements),
            "decisions": len(self.decisions),
            "frustrations": len(self.frustrations),
            "preferences": len(self.preferences),
            "tool_usage": self.tool_usage,
            "context_overflows": len(self.context_overflows),
            "correction_texts": [c.content[:200] for c in self.corrections],
            "encouragement_texts": [e.content[:200] for e in self.encouragements],
            "decision_texts": [d.content[:200] for d in self.decisions],
            "preference_texts": [p.content[:200] for p in self.preferences],
        }


# --- Core analysis functions ---


def analyze_session(file_path: Path) -> SessionAnalysis:
    """Analyze a Claude Code JSONL session file.

    Extracts user signals, tool patterns, context overflows,
    and conversation flow from raw session data.
    """
    analysis = SessionAnalysis(
        source_file=str(file_path),
        session_id=file_path.stem,
    )

    if not file_path.exists():
        return analysis

    records = _load_records(file_path)
    analysis.total_records = len(records)

    # Extract timeline
    timestamps = _extract_timestamps(records)
    if timestamps:
        analysis.start_time = min(timestamps).isoformat()
        analysis.end_time = max(timestamps).isoformat()
        analysis.duration_seconds = (max(timestamps) - min(timestamps)).total_seconds()

    # Process each record
    for record in records:
        record_type = record.get("type", "")

        if record_type == "user":
            _process_user_record(record, analysis)

        elif record_type == "assistant":
            _process_assistant_record(record, analysis)

    return analysis


def _load_records(file_path: Path) -> list[dict[str, Any]]:
    """Load all JSON records from a JSONL file."""
    records: list[dict[str, Any]] = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def _extract_timestamps(records: list[dict[str, Any]]) -> list[datetime]:
    """Extract and parse all timestamps from records."""
    timestamps: list[datetime] = []
    for record in records:
        ts = record.get("timestamp", "")
        if not ts:
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                timestamps.append(dt)
            elif isinstance(ts, (int, float)):
                epoch = ts / 1000 if ts > 1e12 else ts
                timestamps.append(datetime.fromtimestamp(epoch, tz=timezone.utc))
        except (ValueError, OSError):
            continue
    return timestamps


def _extract_user_text(record: dict[str, Any]) -> str:
    """Extract clean user text from a user record, stripping system reminders."""
    msg = record.get("message", {})
    content = msg.get("content", "")

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        content = " ".join(parts)

    if not isinstance(content, str):
        content = str(content)

    # Strip system reminders
    if "<system-reminder>" in content:
        content = content[: content.index("<system-reminder>")]

    return content.strip()


def _detect_signals(
    text: str,
    patterns: tuple[str, ...],
    signal_type: str,
    timestamp: str,
) -> UserSignal | None:
    """Check text against patterns and return a signal if any match."""
    text_lower = text.lower()
    matched = []
    for pattern in patterns:
        if re.search(pattern, text_lower):
            matched.append(pattern)

    if matched:
        return UserSignal(
            signal_type=signal_type,
            content=text[:300],
            timestamp=timestamp,
            patterns_matched=matched,
        )
    return None


def _process_user_record(record: dict[str, Any], analysis: SessionAnalysis) -> None:
    """Process a user record for signals and patterns."""
    text = _extract_user_text(record)
    if not text:
        return

    analysis.user_messages += 1
    analysis.user_message_texts.append(text)
    timestamp = record.get("timestamp", "")

    # Detect context overflow (session continuation)
    if "continued from a previous conversation" in text.lower():
        analysis.context_overflows.append(
            ContextOverflow(
                timestamp=timestamp,
                message_index=analysis.user_messages,
                continuation_text=text[:200],
            ),
        )
        return  # Don't classify continuation messages as signals

    # Detect signals — check frustration BEFORE correction, because a message
    # can match both ("don't" appears in frustration AND correction patterns).
    # If it's frustration, it's venting — not an actionable correction.
    frustration = _detect_signals(text, FRUSTRATION_PATTERNS, "frustration", timestamp)
    if frustration:
        analysis.frustrations.append(frustration)
        # Don't also classify as correction — frustration takes priority
    else:
        correction = _detect_signals(text, CORRECTION_PATTERNS, "correction", timestamp)
        if correction:
            analysis.corrections.append(correction)

    encouragement = _detect_signals(text, ENCOURAGEMENT_PATTERNS, "encouragement", timestamp)
    if encouragement:
        analysis.encouragements.append(encouragement)

    decision = _detect_signals(text, DECISION_PATTERNS, "decision", timestamp)
    if decision:
        analysis.decisions.append(decision)

    preference = _detect_signals(text, PREFERENCE_PATTERNS, "preference", timestamp)
    if preference:
        analysis.preferences.append(preference)


def _process_assistant_record(record: dict[str, Any], analysis: SessionAnalysis) -> None:
    """Process an assistant record for tool usage and model info."""
    msg = record.get("message", {})
    timestamp = record.get("timestamp", "")

    # Track model
    model = msg.get("model", "")
    if model and model != "<synthetic>":
        analysis.models_used[model] = analysis.models_used.get(model, 0) + 1

    # Process content blocks
    for block in msg.get("content", []):
        if not isinstance(block, dict):
            continue

        block_type = block.get("type", "")

        if block_type == "text":
            analysis.assistant_messages += 1

        elif block_type == "tool_use":
            tool_name = block.get("name", "unknown")
            analysis.tool_calls_total += 1
            analysis.tool_usage[tool_name] = analysis.tool_usage.get(tool_name, 0) + 1

            # Summarize tool input
            tool_input = block.get("input", {})
            summary = _summarize_tool_input(tool_name, tool_input)
            analysis.tool_sequence.append(
                ToolCall(
                    tool_name=tool_name,
                    timestamp=timestamp,
                    input_summary=summary,
                ),
            )


def _summarize_tool_input(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Create a brief summary of what a tool call did."""
    if tool_name in ("Read", "read"):
        return str(tool_input.get("file_path", ""))[:100]
    if tool_name in ("Write", "write"):
        return str(tool_input.get("file_path", ""))[:100]
    if tool_name in ("Edit", "edit"):
        return str(tool_input.get("file_path", ""))[:100]
    if tool_name in ("Bash", "bash"):
        return str(tool_input.get("command", ""))[:100]
    if tool_name == "Glob":
        return str(tool_input.get("pattern", ""))[:100]
    if tool_name == "Grep":
        return str(tool_input.get("pattern", ""))[:100]
    if tool_name == "Agent":
        return str(tool_input.get("description", ""))[:100]
    if tool_name == "TodoWrite":
        return "todo update"

    # Generic: first string value
    for v in tool_input.values():
        if isinstance(v, str) and v:
            return v[:80]
    return ""


# --- Discovery functions ---


from divineos.analysis.session_discovery import (  # noqa: E402
    aggregate_analyses as aggregate_analyses,
    analyze_all_sessions as analyze_all_sessions,
    find_sessions as find_sessions,
)
