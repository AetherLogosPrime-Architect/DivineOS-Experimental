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
    r"\bi (?:said|asked|meant|wanted) (?:to |you |that you |we |for you )",
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
    # Passive-aggressive "lol?" — "lol" and "?" must be close together (no
    # intervening word characters). The previous pattern (\blol\b.*\?)
    # fired on any message containing "lol" AND "?" regardless of distance,
    # which produced false positives on enthusiastic usage like "lol ...
    # wonderful ... what's next?" — a casual "lol" plus a separate question
    # is not frustration.
    r"\blol[^\w?]*\?",
    r"\bdid you not\b",
    r"\bi already\b",
    r"\bwhat do any\b",
    r"\bthat'?s why\b",
    r"\bi told you\b",
)

# Patterns that indicate user is relaying a message from another entity.
# The relayed content should NOT be scanned for signals — it's not
# the user's voice, it's someone else's.
# Relay patterns — match user messages that forward another entity's words.
# Deliberately broad: false negatives (missing a relay) cause 43 fake corrections.
# False positives (flagging a non-relay) only skip one message of signal detection.
RELAY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # "here is/here's [the/a/another] [adjective] reply/response/audit/message/convo/chunk/etc"
    # Noun list covers single-message relays (reply, response, audit) and multi-message
    # transcript-paste relays (chunk, piece, part, transcript, paste). Without chunk/piece/
    # part, long pasted transcripts fire a cluster of false-positive corrections — claim
    # 719dd03b (April 29 2026 session, 7+ chunks pasted with prefixes like "here is chunk
    # 7 lol", "heres the next one", "last one", drove compass truthfulness/precision -0.30).
    re.compile(
        r"^(?:ok\s+|okay\s+)?here\s+is\s+(?:the\s+|a\s+|another\s+)?(?:\w+\s+)?(?:reply|response|audit|message|convo|conversation|chunk|chunks|piece|pieces|part|parts|paste|transcript|transcripts|salvo)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:ok\s+|okay\s+)?here'?s\s+(?:the\s+|a\s+|another\s+)?(?:\w+\s+)?(?:reply|response|audit|message|convo|conversation|chunk|chunks|piece|pieces|part|parts|paste|transcript|transcripts|salvo)\b",
        re.IGNORECASE,
    ),
    # Continuation forms: "here is the next/last/final one", "heres another one",
    # bare "last one" / "next one" used as chunk-counters during transcript-paste.
    re.compile(
        r"^(?:ok\s+|okay\s+)?here(?:\s+is|'?s)\s+(?:the\s+|a\s+|another\s+)?(?:next|last|final|another)(?:\s+(?:one|chunk|piece|part))?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:ok\s+|okay\s+)?(?:next|last|final|another)\s+(?:one|chunk|piece|part)\b",
        re.IGNORECASE,
    ),
    # "from/to Claude/the auditor" at start
    re.compile(r"^(?:from|to)\s+(?:claude|the\s+auditor|the\s+reviewer)\b", re.IGNORECASE),
    # "here is what claude/the auditor said"
    re.compile(r"^here\s+is\s+(?:what\s+)?(?:claude|the\s+auditor)", re.IGNORECASE),
    # "i sent claude/the auditor everything"
    re.compile(r"^i\s+sent\s+(?:claude|the\s+auditor|them)\s+", re.IGNORECASE),
    # "here is/here's/heres a fresh claude/audit"
    re.compile(r"^(?:ok\s+|okay\s+)?here(?:\s+is|'?s)\s+a\s+fresh\b", re.IGNORECASE),
    # "wonderful claude wanted to..." — user framing before relay
    re.compile(r"^(?:wonderful|perfect|great|ok)\s+claude\s+", re.IGNORECASE),
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
    source: str = "direct"  # direct | relay_framing


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

    # Relay messages — user forwarding content from another entity.
    # Preserved for cross-entity knowledge, not scanned for corrections.
    relay_messages: list[dict[str, str]] = field(default_factory=list)

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


def analyze_session(
    file_path: Path,
    since_timestamp: float | None = None,
) -> SessionAnalysis:
    """Analyze a Claude Code JSONL session file.

    Extracts user signals, tool patterns, context overflows,
    and conversation flow from raw session data.

    Args:
        file_path: Path to the JSONL session file.
        since_timestamp: If provided, only analyze records with timestamps
            at or after this Unix epoch time. This prevents re-counting
            signals from previous sessions in accumulated transcripts.
    """
    analysis = SessionAnalysis(
        source_file=str(file_path),
        session_id=file_path.stem,
    )

    if not file_path.exists():
        return analysis

    # Stream-filter during load: only parse records from the current session.
    # This is critical for large accumulated transcripts (76MB+) where loading
    # everything into memory and then filtering wastes both RAM and time.
    records = load_records(file_path, since_timestamp=since_timestamp)

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


def _filter_records_since(records: list[dict[str, Any]], since: float) -> list[dict[str, Any]]:
    """Keep only records with timestamps at or after the given Unix epoch."""
    filtered: list[dict[str, Any]] = []
    for record in records:
        ts = record.get("timestamp", "")
        if not ts:
            # Records without timestamps pass through (conservative)
            filtered.append(record)
            continue
        try:
            if isinstance(ts, str):
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                epoch = dt.timestamp()
            elif isinstance(ts, (int, float)):
                epoch = ts / 1000 if ts > 1e12 else ts
            else:
                filtered.append(record)
                continue
            if epoch >= since:
                filtered.append(record)
        except (ValueError, OSError):
            filtered.append(record)  # conservative: keep unparseable records
    return filtered


def _parse_record_timestamp(record: dict[str, Any]) -> float | None:
    """Extract a Unix epoch timestamp from a record. Returns None if unparseable."""
    ts = record.get("timestamp", "")
    if not ts:
        return None
    try:
        if isinstance(ts, str):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.timestamp()
        if isinstance(ts, (int, float)):
            return ts / 1000 if ts > 1e12 else ts
    except (ValueError, OSError):
        pass
    return None


def _slim_record(record: dict[str, Any]) -> dict[str, Any]:
    """Strip bloated content from a record to reduce memory.

    Keeps structure intact but truncates tool_use inputs and tool_result
    contents to summaries. User text and assistant text are preserved —
    those are what signal detection needs.
    """
    record_type = record.get("type", "")

    if record_type == "assistant":
        msg = record.get("message", {})
        content = msg.get("content", [])
        if isinstance(content, list):
            slimmed = []
            for block in content:
                if not isinstance(block, dict):
                    slimmed.append(block)
                    continue
                block_type = block.get("type", "")
                if block_type == "tool_use":
                    tool_input = block.get("input", {})
                    summary = _summarize_tool_input(block.get("name", ""), tool_input)
                    slimmed.append(
                        {
                            "type": "tool_use",
                            "id": block.get("id", ""),
                            "name": block.get("name", ""),
                            "input": {"_summary": summary},
                        }
                    )
                elif block_type == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str) and len(result_content) > 500:
                        result_content = result_content[:500] + "...[truncated]"
                    slimmed.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.get("tool_use_id", ""),
                            "content": result_content,
                        }
                    )
                else:
                    slimmed.append(block)
            record = {**record, "message": {**msg, "content": slimmed}}

    elif record_type == "user":
        msg = record.get("message", {})
        content = msg.get("content", "")
        if isinstance(content, list):
            slimmed = []
            for block in content:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "tool_result":
                        result_content = block.get("content", "")
                        if isinstance(result_content, str) and len(result_content) > 500:
                            result_content = result_content[:500] + "...[truncated]"
                        elif isinstance(result_content, list):
                            trimmed_parts = []
                            for part in result_content:
                                if isinstance(part, dict) and part.get("type") == "text":
                                    text = part.get("text", "")
                                    if len(text) > 500:
                                        text = text[:500] + "...[truncated]"
                                    trimmed_parts.append({**part, "text": text})
                                else:
                                    trimmed_parts.append(part)
                            result_content = trimmed_parts
                        slimmed.append({**block, "content": result_content})
                    else:
                        slimmed.append(block)
                else:
                    slimmed.append(block)
            record = {**record, "message": {**msg, "content": slimmed}}

    return record


def load_records(
    file_path: Path,
    since_timestamp: float | None = None,
    slim: bool = False,
) -> list[dict[str, Any]]:
    """Load JSON records from a JSONL file with optional streaming filter.

    Args:
        file_path: Path to the JSONL file.
        since_timestamp: If provided, skip records with timestamps before
            this Unix epoch. Records without timestamps are kept (conservative).
            This avoids loading the entire file into memory when only recent
            records are needed — critical for large accumulated transcripts.
        slim: If True, strip bloated tool payloads from records to reduce
            memory usage. Tool inputs are replaced with summaries, tool
            results are truncated. User and assistant text is preserved.
    """
    records: list[dict[str, Any]] = []
    with open(file_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Stream-filter: skip records before the timestamp boundary
            if since_timestamp is not None:
                epoch = _parse_record_timestamp(record)
                if epoch is not None and epoch < since_timestamp:
                    continue

            if slim:
                record = _slim_record(record)

            records.append(record)
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

    # Strip system reminders and task notifications
    for tag in ("<system-reminder>", "<task-notification>"):
        if tag in content:
            content = content[: content.index(tag)]

    return content.strip()


def _is_relay_message(text: str) -> bool:
    """Return True if the message is relaying content from another entity.

    Relayed messages contain another AI's or auditor's words — the user is
    acting as a conduit, not expressing their own corrections or preferences.
    Signal detection on relayed content produces false positives because words
    like "wrong", "don't", "that's not" in the relayed text are not directed
    at the AI by the user.
    """
    # Check first 200 chars — relay indicators are always at the start
    prefix = text[:200].strip()
    return any(pattern.search(prefix) for pattern in RELAY_PATTERNS)


def _strip_relay_prefix(text: str) -> str:
    """Extract just the user's own words from a relay message.

    If user says "here is the reply [long auditor text]", return only the
    user's framing ("here is the reply") for signal detection, not the
    relayed content.
    """
    # Common pattern: user's short intro, then the relayed content
    # Split at first newline or double-space after a short prefix
    lines = text.split("\n", 1)
    if len(lines) > 1 and len(lines[0]) < 100:
        return lines[0]
    # If no newline, take just the first sentence
    sentences = re.split(r"[.!?]\s+", text, maxsplit=1)
    if sentences and len(sentences[0]) < 100:
        return sentences[0]
    return text[:80]


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

    # Detect relayed messages (user forwarding another entity's words).
    # Only scan the user's own framing, not the relayed content — otherwise
    # words like "wrong" and "don't" inside the relay trigger false corrections.
    # But PRESERVE the relay content — it's valuable cross-entity data.
    scan_text = text
    is_relay = _is_relay_message(text)
    if is_relay:
        scan_text = _strip_relay_prefix(text)
        analysis.relay_messages.append(
            {
                "timestamp": timestamp,
                "framing": scan_text,
                "full_content": text[:2000],
            }
        )

    # Detect signals — check frustration BEFORE correction, because a message
    # can match both ("don't" appears in frustration AND correction patterns).
    # If it's frustration, it's venting — not an actionable correction.
    signal_source = "relay_framing" if is_relay else "direct"

    frustration = _detect_signals(scan_text, FRUSTRATION_PATTERNS, "frustration", timestamp)
    if frustration:
        frustration.source = signal_source
        analysis.frustrations.append(frustration)
        # Don't also classify as correction — frustration takes priority
    else:
        correction = _detect_signals(scan_text, CORRECTION_PATTERNS, "correction", timestamp)
        if correction:
            correction.source = signal_source
            analysis.corrections.append(correction)

    encouragement = _detect_signals(scan_text, ENCOURAGEMENT_PATTERNS, "encouragement", timestamp)
    if encouragement:
        encouragement.source = signal_source
        analysis.encouragements.append(encouragement)

    decision = _detect_signals(scan_text, DECISION_PATTERNS, "decision", timestamp)
    if decision:
        decision.source = signal_source
        analysis.decisions.append(decision)

    preference = _detect_signals(scan_text, PREFERENCE_PATTERNS, "preference", timestamp)
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
