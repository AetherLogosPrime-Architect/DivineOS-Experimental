"""Tone Texture — preserving emotional narrative across sessions.

Not just "2 corrections" but "frustrated when I over-engineered,
recovered when I simplified." The difference between counting
incidents and understanding what happened.
"""

import time
from typing import Any

from loguru import logger

from divineos.analysis.session_analyzer import (
    CORRECTION_PATTERNS,
    ENCOURAGEMENT_PATTERNS,
    FRUSTRATION_PATTERNS,
    _detect_signals,
)
from divineos.core.knowledge import get_connection

# ── Sub-tone patterns ───────────────────────────────────────

_CONFUSED_PATTERNS = (
    r"\bwhat do you mean\b",
    r"\bi don'?t understand\b",
    r"\bconfus",
    r"\bhuh\b",
    r"\bwhat\?\b",
    r"\bwait,?\s+what\b",
    r"\bthat makes no sense\b",
    r"\bcan you explain\b",
)

_DISAPPOINTED_PATTERNS = (
    r"\bi expected\b",
    r"\bi thought you\b",
    r"\bi was hoping\b",
    r"\bnot what i wanted\b",
    r"\bthat'?s not quite\b",
    r"\bclose but\b",
)

_EXCITED_PATTERNS = (
    r"\b!{2,}",
    r"\blets go\b",
    r"\blet'?s go\b",
    r"\bomg\b",
    r"\byes!\b",
    r"\bthis is it\b",
    r"\bfinally\b",
)

_GRATEFUL_PATTERNS = (
    r"\bthank",
    r"\bappreciate\b",
    r"\bhelpful\b",
    r"\bsaved me\b",
)


def classify_tone_rich(text: str) -> dict[str, Any]:
    """Classify tone with sub-tone and intensity.

    Returns: {"tone": str, "sub_tone": str, "intensity": float}
    """
    pos = _detect_signals(text, ENCOURAGEMENT_PATTERNS, "pos", "")
    neg_corr = _detect_signals(text, CORRECTION_PATTERNS, "neg", "")
    neg_frust = _detect_signals(text, FRUSTRATION_PATTERNS, "neg", "")

    # Count total pattern matches for intensity
    pos_count = len(pos.patterns_matched) if pos else 0
    neg_count = (len(neg_corr.patterns_matched) if neg_corr else 0) + (
        len(neg_frust.patterns_matched) if neg_frust else 0
    )

    # Determine base tone (same logic as existing _classify_tone)
    if neg_frust:
        tone = "negative"
    elif neg_corr and not pos:
        tone = "negative"
    elif pos and not neg_corr:
        tone = "positive"
    elif pos and neg_corr:
        tone = "neutral"
    else:
        tone = "neutral"

    # Determine sub-tone
    sub_tone = _classify_sub_tone(text, tone)

    # Intensity: 0.3 base + signal density (more pattern hits = more intense)
    total_signals = pos_count + neg_count
    intensity = min(1.0, 0.3 + total_signals * 0.15)

    # Frustration patterns boost intensity
    if neg_frust:
        intensity = min(1.0, intensity + 0.2)

    # Exclamation marks boost intensity
    excl_count = text.count("!")
    if excl_count >= 2:
        intensity = min(1.0, intensity + 0.1)

    return {"tone": tone, "sub_tone": sub_tone, "intensity": round(intensity, 2)}


def _classify_sub_tone(text: str, base_tone: str) -> str:
    """Determine the sub-tone based on text patterns."""
    if base_tone == "negative":
        # Check sub-tone patterns (order: confused > frustrated > disappointed > corrective)
        if _detect_signals(text, _CONFUSED_PATTERNS, "neg", ""):
            return "confused"
        if _detect_signals(text, FRUSTRATION_PATTERNS, "neg", ""):
            return "frustrated"
        if _detect_signals(text, _DISAPPOINTED_PATTERNS, "neg", ""):
            return "disappointed"
        return "corrective"

    if base_tone == "positive":
        if _detect_signals(text, _EXCITED_PATTERNS, "pos", ""):
            return "excited"
        if _detect_signals(text, _GRATEFUL_PATTERNS, "pos", ""):
            return "grateful"
        return "encouraging"

    # Neutral sub-tones
    if "?" in text:
        return "questioning"
    return "informational"


def compute_emotional_arc(
    tone_sequence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute session-level emotional summary from classified messages.

    Args:
        tone_sequence: List of {"tone", "sub_tone", "intensity", "text", "sequence"}
            ordered by message sequence.

    Returns a structured arc with narrative context.
    """
    if not tone_sequence:
        return {
            "arc_type": "silent",
            "overall_tone": "neutral",
            "peak_intensity": 0.0,
            "upset_triggers": [],
            "recovery_actions": [],
            "recovery_velocity": 0.0,
            "narrative": "",
        }

    tones = [m["tone"] for m in tone_sequence]
    intensities = [m["intensity"] for m in tone_sequence]

    # Overall tone: majority vote
    tone_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for t in tones:
        tone_counts[t] = tone_counts.get(t, 0) + 1
    overall = max(tone_counts, key=lambda k: tone_counts[k])

    # Arc type: how did the session flow?
    arc_type = _determine_arc_type(tones)

    # Peak intensity
    peak = max(intensities) if intensities else 0.0

    # Find upset→recovery pairs and measure velocity
    upset_triggers: list[str] = []
    recovery_actions: list[str] = []
    velocities: list[int] = []

    i = 0
    while i < len(tone_sequence):
        if tone_sequence[i]["tone"] == "negative":
            # Capture what was said (the trigger context)
            text = tone_sequence[i].get("text", "")
            if text:
                upset_triggers.append(text[:120])

            # Look for recovery
            for j in range(i + 1, len(tone_sequence)):
                if tone_sequence[j]["tone"] == "positive":
                    velocities.append(j - i)
                    recovery_text = tone_sequence[j].get("text", "")
                    if recovery_text:
                        recovery_actions.append(recovery_text[:120])
                    i = j
                    break
            else:
                # No recovery found
                pass
        i += 1

    avg_velocity = sum(velocities) / len(velocities) if velocities else 0.0

    # Build narrative
    narrative = _build_narrative(
        arc_type, overall, tone_sequence, upset_triggers, recovery_actions, avg_velocity
    )

    return {
        "arc_type": arc_type,
        "overall_tone": overall,
        "peak_intensity": round(peak, 2),
        "upset_triggers": upset_triggers[:3],
        "recovery_actions": recovery_actions[:3],
        "recovery_velocity": round(avg_velocity, 1),
        "narrative": narrative,
    }


def _determine_arc_type(tones: list[str]) -> str:
    """Classify the emotional trajectory of a session."""
    if not tones:
        return "silent"

    n = len(tones)
    if n < 3:
        return "brief"

    neg_count = tones.count("negative")
    pos_count = tones.count("positive")

    # Check for recovery arc: negative somewhere in middle, positive later
    first_neg = next((i for i, t in enumerate(tones) if t == "negative"), -1)
    last_pos = next((i for i in range(n - 1, -1, -1) if tones[i] == "positive"), -1)

    if first_neg >= 0 and last_pos > first_neg:
        return "recovery"

    # Check for steady positive
    if neg_count == 0 and pos_count >= n * 0.4:
        return "steady_positive"

    # Check for declining (ends negative)
    if neg_count > 0 and tones[-1] == "negative":
        return "declining"

    # Check for volatile (multiple swings)
    shifts = sum(1 for i in range(1, n) if tones[i] != tones[i - 1])
    if shifts >= n * 0.5:
        return "volatile"

    return "steady"


def _build_narrative(
    arc_type: str,
    overall: str,
    sequence: list[dict[str, Any]],
    triggers: list[str],
    recoveries: list[str],
    velocity: float,
) -> str:
    """Build a one-sentence narrative of the emotional arc."""
    n = len(sequence)

    if arc_type == "silent":
        return ""
    if arc_type == "brief":
        return f"Brief session ({n} messages), overall {overall}."
    if arc_type == "steady_positive":
        return f"Consistently positive session across {n} messages."
    if arc_type == "steady":
        return f"Steady session across {n} messages, overall {overall}."

    if arc_type == "recovery":
        trigger_hint = ""
        if triggers:
            trigger_hint = f" (triggered by: {triggers[0][:60]})"
        recovery_hint = ""
        if recoveries:
            recovery_hint = f" via {recoveries[0][:60]}"
        speed = "quickly" if velocity <= 2 else "gradually" if velocity <= 5 else "slowly"
        return f"Hit frustration{trigger_hint}, {speed} recovered{recovery_hint}."

    if arc_type == "declining":
        return f"Session ended on a negative note after {n} messages."

    if arc_type == "volatile":
        return f"Emotionally volatile session with frequent shifts across {n} messages."

    return f"Session with {n} messages, overall {overall}."


# ── Persistence ─────────────────────────────────────────────


def init_tone_texture_table() -> None:
    """Create tone_texture table for per-session emotional arcs."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tone_texture (
                session_id       TEXT PRIMARY KEY,
                recorded_at      REAL NOT NULL,
                arc_type         TEXT NOT NULL,
                overall_tone     TEXT NOT NULL,
                peak_intensity   REAL NOT NULL DEFAULT 0.0,
                recovery_velocity REAL NOT NULL DEFAULT 0.0,
                upset_count      INTEGER NOT NULL DEFAULT 0,
                recovery_count   INTEGER NOT NULL DEFAULT 0,
                narrative        TEXT NOT NULL DEFAULT ''
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tone_texture_time
            ON tone_texture(recorded_at)
        """)
        conn.commit()
    finally:
        conn.close()


def record_session_tone(session_id: str, arc: dict[str, Any]) -> None:
    """Store a session's emotional arc."""
    init_tone_texture_table()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO tone_texture "
            "(session_id, recorded_at, arc_type, overall_tone, peak_intensity, "
            "recovery_velocity, upset_count, recovery_count, narrative) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                time.time(),
                arc.get("arc_type", "unknown"),
                arc.get("overall_tone", "neutral"),
                arc.get("peak_intensity", 0.0),
                arc.get("recovery_velocity", 0.0),
                len(arc.get("upset_triggers", [])),
                len(arc.get("recovery_actions", [])),
                arc.get("narrative", ""),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug("Tone texture recorded for %s", session_id[:12])


def get_tone_history(limit: int = 10) -> list[dict[str, Any]]:
    """Retrieve emotional arcs across sessions, newest first."""
    init_tone_texture_table()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT session_id, recorded_at, arc_type, overall_tone, "
            "peak_intensity, recovery_velocity, upset_count, recovery_count, narrative "
            "FROM tone_texture ORDER BY recorded_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "session_id",
        "recorded_at",
        "arc_type",
        "overall_tone",
        "peak_intensity",
        "recovery_velocity",
        "upset_count",
        "recovery_count",
        "narrative",
    ]
    return [dict(zip(cols, row)) for row in rows]


def format_tone_insight(history: list[dict[str, Any]]) -> str:
    """Format cross-session emotional patterns for display."""
    if not history:
        return ""

    n = len(history)
    arc_types = [h["arc_type"] for h in history]
    recovery_count = sum(h["recovery_count"] for h in history)
    upset_count = sum(h["upset_count"] for h in history)
    avg_peak = sum(h["peak_intensity"] for h in history) / n

    # Most common arc type
    type_counts: dict[str, int] = {}
    for at in arc_types:
        type_counts[at] = type_counts.get(at, 0) + 1
    dominant_arc = max(type_counts, key=lambda k: type_counts[k])

    parts = [f"**Tone:** {dominant_arc} pattern across {n} sessions"]

    if upset_count > 0:
        ratio = recovery_count / upset_count if upset_count else 0
        parts.append(
            f"  {upset_count} upsets, {recovery_count} recoveries ({ratio:.0%} recovery rate)"
        )

        # Average recovery velocity across sessions that had recoveries
        velocities = [h["recovery_velocity"] for h in history if h["recovery_velocity"] > 0]
        if velocities:
            avg_vel = sum(velocities) / len(velocities)
            speed = "fast" if avg_vel <= 2 else "moderate" if avg_vel <= 5 else "slow"
            parts.append(f"  Recovery speed: {speed} (avg {avg_vel:.1f} messages)")

    if avg_peak > 0.6:
        parts.append(f"  Emotional intensity: high (avg peak {avg_peak:.2f})")

    return "\n".join(parts)
