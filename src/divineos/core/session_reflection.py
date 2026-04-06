"""Session reflection -- structured self-assessment before regex extraction.

The regex-based signal detector catches keyword patterns but cannot
distinguish genuine praise from constructive challenge, or a correction
from frustration. This module produces a structured reflection from
session data that the extraction pipeline uses alongside regex signals.

The reflection answers: what kind of session was this, what went well,
what went wrong, and what should I carry forward?
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionReflection:
    """Structured self-assessment of a session."""

    session_id: str = ""

    # Session character -- what kind of work happened
    character: str = ""  # building, debugging, discussing, reviewing, mixed
    character_evidence: list[str] = field(default_factory=list)

    # What went well (with evidence)
    went_well: list[str] = field(default_factory=list)

    # What went wrong (with evidence)
    went_wrong: list[str] = field(default_factory=list)

    # Learnings -- distilled from the session arc, not just individual signals
    learnings: list[str] = field(default_factory=list)

    # Dominant topics
    topics: list[str] = field(default_factory=list)

    # Correction-to-recovery arcs: pairs of (what went wrong, how it was fixed)
    recovery_arcs: list[tuple[str, str]] = field(default_factory=list)

    # Session stats for context
    user_messages: int = 0
    tool_calls: int = 0
    corrections: int = 0
    encouragements: int = 0

    def summary(self) -> str:
        """One-line summary for pipeline output."""
        parts = [f"Session character: {self.character}"]
        if self.went_well:
            parts.append(f"{len(self.went_well)} things went well")
        if self.went_wrong:
            parts.append(f"{len(self.went_wrong)} things went wrong")
        if self.learnings:
            parts.append(f"{len(self.learnings)} learnings")
        if self.recovery_arcs:
            parts.append(f"{len(self.recovery_arcs)} recovery arcs")
        return " | ".join(parts)


# ── Character Detection ─────────────────────────────────────────────


def _detect_character(
    analysis: Any,
    records: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    """Detect the dominant character of a session from tool patterns and content.

    Returns (character, evidence_list).
    """
    tool_usage = getattr(analysis, "tool_usage", {})
    user_messages = getattr(analysis, "user_messages", 0)
    corrections = len(getattr(analysis, "corrections", []))
    tool_total = getattr(analysis, "tool_calls_total", 0)

    evidence: list[str] = []

    # Count tool categories
    write_tools = sum(tool_usage.get(t, 0) for t in ("Write", "Edit"))
    read_tools = sum(tool_usage.get(t, 0) for t in ("Read", "Glob", "Grep"))
    bash_count = tool_usage.get("Bash", 0)
    agent_count = tool_usage.get("Agent", 0)

    # Heuristics for session character
    if tool_total == 0 and user_messages > 3:
        evidence.append(f"{user_messages} messages, 0 tool calls -- pure conversation")
        return "discussing", evidence

    if write_tools > 5 and corrections < 3:
        evidence.append(
            f"{write_tools} write/edit calls, {corrections} corrections -- productive building"
        )
        return "building", evidence

    if corrections > 3 and write_tools > 3:
        evidence.append(
            f"{corrections} corrections during {write_tools} edits -- iterative debugging"
        )
        return "debugging", evidence

    if read_tools > write_tools * 2 and read_tools > 5:
        evidence.append(f"{read_tools} read/search vs {write_tools} write -- review/exploration")
        return "reviewing", evidence

    if bash_count > 10 and write_tools < 3:
        evidence.append(f"{bash_count} bash calls, {write_tools} writes -- testing/investigation")
        return "debugging", evidence

    if agent_count > 3:
        evidence.append(f"{agent_count} agent calls -- multi-step research")
        return "reviewing", evidence

    # Mixed or unclear
    evidence.append(f"{tool_total} tools, {user_messages} messages, {corrections} corrections")
    return "mixed", evidence


# ── Arc Detection ────────────────────────────────────────────────────


def _detect_recovery_arcs(
    analysis: Any,
    records: list[dict[str, Any]],
) -> list[tuple[str, str]]:
    """Find correction-then-recovery arcs in the session.

    A recovery arc is: user corrects something -> AI fixes it -> user confirms.
    These are success stories, not just failures.
    """
    arcs: list[tuple[str, str]] = []
    corrections = getattr(analysis, "corrections", [])
    encouragements = getattr(analysis, "encouragements", [])

    if not corrections or not encouragements:
        return arcs

    # Simple heuristic: if a correction is followed by an encouragement
    # within a few messages, that's a recovery arc.
    correction_texts = [c.content[:100] for c in corrections]
    encouragement_texts = [e.content[:100] for e in encouragements]

    # Build a timeline of user messages
    user_timeline: list[tuple[str, str]] = []  # (type, text)
    for rec in records:
        if rec.get("type") != "user":
            continue
        msg = rec.get("message", {})
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
        if "<system-reminder>" in content:
            content = content[: content.index("<system-reminder>")]
        content = content.strip()
        if not content:
            continue

        # Classify this message
        is_correction = any(content[:100] == ct for ct in correction_texts)
        is_encouragement = any(content[:100] == et for et in encouragement_texts)
        if is_correction:
            user_timeline.append(("correction", content[:150]))
        elif is_encouragement:
            user_timeline.append(("encouragement", content[:150]))
        else:
            user_timeline.append(("other", content[:150]))

    # Find correction -> encouragement pairs (within 5 messages)
    for i, (msg_type, text) in enumerate(user_timeline):
        if msg_type != "correction":
            continue
        for j in range(i + 1, min(i + 6, len(user_timeline))):
            if user_timeline[j][0] == "encouragement":
                arcs.append((text, user_timeline[j][1]))
                break

    return arcs


# ── Learning Extraction ──────────────────────────────────────────────


def _extract_learnings(
    analysis: Any,
    records: list[dict[str, Any]],
    character: str,
    recovery_arcs: list[tuple[str, str]],
) -> list[str]:
    """Extract learnings from the session as a whole, not individual signals.

    This produces insights that regex can't -- like "this session started
    rough but improved after I changed approach" or "the user gave positive
    feedback on the code but the test suite showed problems."
    """
    learnings: list[str] = []
    corrections = getattr(analysis, "corrections", [])
    encouragements = getattr(analysis, "encouragements", [])
    preferences = getattr(analysis, "preferences", [])

    # Recovery arcs are success stories
    for correction_text, recovery_text in recovery_arcs:
        learnings.append(
            f"I was corrected ({_truncate(correction_text, 80)}) "
            f"but recovered ({_truncate(recovery_text, 80)}). "
            f"The recovery matters as much as the mistake."
        )

    # Session-level patterns
    if len(corrections) == 0 and len(encouragements) > 2:
        learnings.append(
            "Session had zero corrections and multiple encouragements -- "
            "approach was well-calibrated to user needs."
        )

    if len(corrections) > 3 and character == "building":
        learnings.append(
            f"Session had {len(corrections)} corrections during active building -- "
            "I was moving too fast or misunderstanding requirements."
        )

    if len(corrections) > 0 and len(corrections) <= 2 and len(encouragements) > 0:
        learnings.append(
            "Session had minor corrections followed by positive feedback -- "
            "normal iteration, not a pattern problem."
        )

    # Preference signals indicate calibration opportunities
    if preferences:
        pref_texts = [p.content[:60] for p in preferences[:3]]
        learnings.append(
            f"User expressed {len(preferences)} preferences this session. "
            f"Key signals: {'; '.join(pref_texts)}"
        )

    return learnings


# ── What Went Well / Wrong ───────────────────────────────────────────


def _assess_went_well(
    analysis: Any,
    records: list[dict[str, Any]],
    character: str,
) -> list[str]:
    """Identify what went well in the session."""
    well: list[str] = []
    encouragements = getattr(analysis, "encouragements", [])
    corrections = getattr(analysis, "corrections", [])
    tool_total = getattr(analysis, "tool_calls_total", 0)

    if encouragements:
        well.append(f"Received {len(encouragements)} positive signals from user.")

    if tool_total > 10 and len(corrections) == 0:
        well.append(f"Completed {tool_total} tool operations with zero corrections.")

    if character == "building" and len(corrections) <= 1:
        well.append("Productive building session with minimal friction.")

    # Check for test runs that passed
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message", {})
        for block in msg.get("content", []):
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") == "Bash":
                cmd = block.get("input", {}).get("command", "")
                if "pytest" in cmd:
                    well.append("Ran tests during session (test-driven approach).")
                    break
        else:
            continue
        break

    return well


def _assess_went_wrong(
    analysis: Any,
    records: list[dict[str, Any]],
    character: str,
) -> list[str]:
    """Identify what went wrong in the session."""
    wrong: list[str] = []
    corrections = getattr(analysis, "corrections", [])
    frustrations = getattr(analysis, "frustrations", [])

    for correction in corrections:
        text = correction.content[:120].replace("\n", " ")
        wrong.append(f"Corrected: {text}")

    if frustrations:
        wrong.append(f"User showed frustration {len(frustrations)} time(s).")

    # Detect repeated file edits (sign of struggle).
    # High-traffic files (hud, cli init, pipeline, readme) are natural edit
    # targets during feature work — use a higher threshold for them.
    _HIGH_TRAFFIC_FILES = frozenset(
        {
            "hud.py",
            "__init__.py",
            "session_pipeline.py",
            "pipeline_phases.py",
            "pipeline_gates.py",
            "CLAUDE.md",
            "README.md",
            "seed.json",
            "_base.py",
            "retrieval.py",
        }
    )
    tool_sequence = getattr(analysis, "tool_sequence", [])
    file_edit_counts: dict[str, int] = {}
    for tc in tool_sequence:
        if tc.tool_name in ("Edit", "Write") and tc.input_summary:
            fp = tc.input_summary.split("/")[-1] if "/" in tc.input_summary else tc.input_summary
            # Strip backslash paths too
            if "\\" in fp:
                fp = fp.split("\\")[-1]
            file_edit_counts[fp] = file_edit_counts.get(fp, 0) + 1

    for fp, count in file_edit_counts.items():
        threshold = 20 if fp in _HIGH_TRAFFIC_FILES else 10
        if count > threshold:
            wrong.append(f"Edited {fp} {count} times (threshold {threshold}) -- possible struggle.")

    return wrong


# ── Topic Extraction ─────────────────────────────────────────────────


def _extract_topics(analysis: Any) -> list[str]:
    """Extract dominant topics from user messages."""
    from divineos.core.knowledge._text import extract_session_topics

    user_texts = getattr(analysis, "user_message_texts", [])
    return extract_session_topics(user_texts)[:5]


# ── Main Entry Point ─────────────────────────────────────────────────


def build_session_reflection(
    analysis: Any,
    records: list[dict[str, Any]],
) -> SessionReflection:
    """Build a structured self-assessment of the session.

    This runs BEFORE regex-based extraction and provides context that
    regex patterns cannot capture: session character, recovery arcs,
    overall trajectory, and session-level learnings.
    """
    reflection = SessionReflection(
        session_id=getattr(analysis, "session_id", ""),
        user_messages=getattr(analysis, "user_messages", 0),
        tool_calls=getattr(analysis, "tool_calls_total", 0),
        corrections=len(getattr(analysis, "corrections", [])),
        encouragements=len(getattr(analysis, "encouragements", [])),
    )

    # Character detection
    reflection.character, reflection.character_evidence = _detect_character(analysis, records)

    # Recovery arcs (correction -> positive feedback)
    reflection.recovery_arcs = _detect_recovery_arcs(analysis, records)

    # What went well / wrong
    reflection.went_well = _assess_went_well(analysis, records, reflection.character)
    reflection.went_wrong = _assess_went_wrong(analysis, records, reflection.character)

    # Learnings from the session arc
    reflection.learnings = _extract_learnings(
        analysis, records, reflection.character, reflection.recovery_arcs
    )

    # Topics
    reflection.topics = _extract_topics(analysis)

    return reflection


# ── Helpers ──────────────────────────────────────────────────────────


def _truncate(text: str, length: int) -> str:
    """Truncate text to length, adding ... if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."
