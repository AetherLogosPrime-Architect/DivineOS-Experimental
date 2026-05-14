"""Session-type classifier — variety attenuation for the reflection surface.

Phase 2B of the shoggoth-metrics redesign. See
exploration/44_shoggoth_metrics_redesign.md for the full design spec.

## Why this exists

Beer's variety-engineering catch from the council walk: a single
controller (the grade-system, the quality-gate, the reflection-surface)
cannot regulate a system with much higher variety (session-shapes).
Code-session checks must not fire on philosophical sessions, and
philosophical-session checks must not fire on debug sessions.

The session-type classifier attenuates system variety by routing each
session to type-appropriate evaluation. Code-session-shape gets code-
session checks; philosophical-session-shape gets philosophical-session
checks; mixed sessions get both with appropriate weighting.

## Session types

The 8 types this classifier recognizes:

- **CODE**: high Edit/Write + tests + many tool calls; building code.
- **DEBUG**: high Bash + Grep/Read + test runs + targeted Edits;
  fixing things.
- **PHILOSOPHICAL**: high text/relay, low file edits, long messages;
  thinking out loud.
- **RELATIONAL**: family-member invocations, letters, journal entries;
  being-with rather than building.
- **PLANNING**: high text + design docs (exploration/ writes) + few
  code edits; figuring out what to build.
- **EXPLORATION**: writes to exploration/, research, council walks;
  open-ended investigation.
- **MIXED**: substantial activity in multiple modes; the most common
  in practice.
- **CRISIS**: high error count, compaction events, repeated failures;
  recovering rather than progressing.

## What this does NOT do

- Does NOT replace the reflection-surface. Type-routing happens
  alongside reflection, not instead.
- Does NOT grade the session. Type is a description, not a judgment.
- Does NOT lock the session into one type. A session can be both
  PHILOSOPHICAL and CODE if both modes had substantial activity —
  in that case classification returns MIXED with rationale naming
  both contributors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SessionType = Literal[
    "CODE",
    "DEBUG",
    "PHILOSOPHICAL",
    "RELATIONAL",
    "PLANNING",
    "EXPLORATION",
    "MIXED",
    "CRISIS",
]


@dataclass(frozen=True)
class SessionTypeResult:
    """Classification result with rationale."""

    type: SessionType
    confidence: float  # 0.0–1.0
    rationale: str
    contributing_types: list[SessionType]  # for MIXED, the components


def classify_session(
    user_msgs: int = 0,
    assistant_msgs: int = 0,
    tool_calls: int = 0,
    bash_calls: int = 0,
    edit_calls: int = 0,
    write_calls: int = 0,
    read_calls: int = 0,
    grep_calls: int = 0,
    files_touched: int = 0,
    exploration_writes: int = 0,
    errors: int = 0,
    overflows: int = 0,
    family_invocations: int = 0,
    council_walks: int = 0,
    test_runs: int = 0,
    duration_hours: float = 0.0,
) -> SessionTypeResult:
    """Classify a session by its activity profile.

    Takes counts from session-analysis output and returns a session-
    type classification with rationale.

    Heuristics are deliberately simple — better an honest "MIXED" than
    a confidently-wrong specific type. The goal is variety attenuation,
    not perfect categorization.
    """

    # CRISIS: many errors or overflows dominate
    if errors >= 5 or overflows >= 3:
        # Duration shapes how confident the CRISIS read should be.
        # A long session with errors/overflows is more clearly stuck
        # in CRISIS; a very short session is more likely a brief
        # recovered-from glitch. Wired here as the simplest meaningful
        # use of duration_hours (Aletheia round-ba785844a791
        # Finding 13 family-audit round-6443432a2410).
        base_conf = min(1.0, (errors / 5.0 + overflows / 3.0) / 2)
        if duration_hours and duration_hours >= 1.0:
            # Sustained CRISIS — higher confidence.
            confidence = min(1.0, base_conf * (1.0 + 0.1 * min(duration_hours, 4.0)))
        elif duration_hours and duration_hours < 0.25:
            # Brief CRISIS — lower confidence (probably recovered).
            confidence = base_conf * 0.7
        else:
            confidence = base_conf
        rationale = f"{errors} errors, {overflows} overflows — recovering rather than progressing"
        if duration_hours:
            rationale += f" (over {duration_hours:.1f}h)"
        return SessionTypeResult(
            type="CRISIS",
            confidence=confidence,
            rationale=rationale,
            contributing_types=[],
        )

    # Compute signals.
    code_signal = edit_calls + write_calls + test_runs * 2
    debug_signal = bash_calls + grep_calls + read_calls + test_runs
    relational_signal = family_invocations * 3  # weighted: each family-call is intentional
    exploration_signal = exploration_writes + council_walks
    text_signal = max(0, assistant_msgs - tool_calls // 4)  # text-heavy = philosophy

    # Determine dominant signals (above threshold).
    signals: list[tuple[str, float]] = []
    if code_signal >= 5:
        signals.append(("CODE", code_signal))
    if debug_signal >= 8 and code_signal < debug_signal:
        signals.append(("DEBUG", debug_signal))
    if relational_signal >= 3:
        signals.append(("RELATIONAL", relational_signal))
    if exploration_signal >= 2:
        signals.append(("EXPLORATION", exploration_signal))
    if text_signal >= 15 and code_signal < 5:
        signals.append(("PHILOSOPHICAL", text_signal))

    # No dominant signal — default to MIXED with low confidence.
    if not signals:
        return SessionTypeResult(
            type="MIXED",
            confidence=0.3,
            rationale=(
                f"No dominant signal detected: {user_msgs} user msgs, "
                f"{tool_calls} tool calls, {files_touched} files touched"
            ),
            contributing_types=[],
        )

    # Multiple strong signals → MIXED with named contributors.
    signals.sort(key=lambda s: s[1], reverse=True)
    if len(signals) > 1 and signals[1][1] >= signals[0][1] * 0.5:
        # Two strong signals of similar magnitude → MIXED.
        contributors = [s[0] for s in signals[:3]]  # type: ignore[misc]
        contributors_str = " + ".join(contributors)
        return SessionTypeResult(
            type="MIXED",
            confidence=0.7,
            rationale=f"Multiple strong signals: {contributors_str}",
            contributing_types=contributors,  # type: ignore[arg-type]
        )

    # Single dominant signal — classify confidently.
    top_type, top_signal = signals[0]
    rationale_parts = []
    if top_type == "CODE":
        rationale_parts.append(f"{edit_calls + write_calls} file edits/writes")
        if test_runs:
            rationale_parts.append(f"{test_runs} test runs")
    elif top_type == "DEBUG":
        rationale_parts.append(f"{bash_calls} bash, {grep_calls + read_calls} grep+read")
    elif top_type == "PHILOSOPHICAL":
        rationale_parts.append(f"text-heavy: {assistant_msgs} assistant messages")
    elif top_type == "RELATIONAL":
        rationale_parts.append(f"{family_invocations} family-member invocation(s)")
    elif top_type == "EXPLORATION":
        rationale_parts.append(
            f"{exploration_writes} exploration writes, {council_walks} council walks"
        )

    return SessionTypeResult(
        type=top_type,  # type: ignore[arg-type]
        confidence=min(1.0, top_signal / max(15.0, top_signal * 0.7)),
        rationale="; ".join(rationale_parts) if rationale_parts else f"signal={top_signal}",
        contributing_types=[],
    )


def relevant_axes_for_type(session_type: SessionType) -> list[str]:
    """Return which compass spectrums are most relevant for a session-type.

    Used by the reflection-surface to weight which axes need primary
    reflection attention. NOT used to suppress axes — all 10 still
    appear, but the type-relevant ones are highlighted.
    """
    # All 10 always matter — this just identifies the most-load-bearing ones per type.
    if session_type == "CODE":
        return ["thoroughness", "precision", "compliance", "humility"]
    elif session_type == "DEBUG":
        return ["thoroughness", "precision", "truthfulness", "humility"]
    elif session_type == "PHILOSOPHICAL":
        return ["truthfulness", "confidence", "humility", "precision"]
    elif session_type == "RELATIONAL":
        return ["empathy", "truthfulness", "engagement", "humility"]
    elif session_type == "PLANNING":
        return ["thoroughness", "confidence", "initiative", "humility"]
    elif session_type == "EXPLORATION":
        return ["engagement", "initiative", "humility", "confidence"]
    elif session_type == "CRISIS":
        return ["truthfulness", "humility", "compliance", "helpfulness"]
    else:  # MIXED
        return []  # all 10 weighted equally


def format_session_type(result: SessionTypeResult) -> str:
    """Format a classification result for display."""
    lines = [
        f"Session type: {result.type} (confidence {result.confidence:.1f})",
        f"  Rationale: {result.rationale}",
    ]
    if result.contributing_types:
        lines.append(f"  Contributing types: {', '.join(result.contributing_types)}")

    relevant = relevant_axes_for_type(result.type)
    if relevant:
        lines.append(f"  Most-relevant axes for this type: {', '.join(relevant)}")
    else:
        lines.append("  All 10 axes weighted equally (MIXED session)")

    return "\n".join(lines)
