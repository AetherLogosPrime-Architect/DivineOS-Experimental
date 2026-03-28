"""Tone Tracking — Detects when user mood shifts and what the AI did in between.

Extracted from session_features.py (Feature 3).
"""

from dataclasses import dataclass
from typing import Any

from divineos.analysis.record_extraction import _extract_tool_calls
from divineos.analysis.session_analyzer import (
    CORRECTION_PATTERNS,
    ENCOURAGEMENT_PATTERNS,
    FRUSTRATION_PATTERNS,
    _detect_signals,
    _extract_user_text,
)


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
    new_sub_tone: str = ""  # frustrated, confused, disappointed, excited, etc.
    new_intensity: float = 0.0  # 0.0-1.0


def _classify_tone(text: str) -> str:
    """Classify a user message as positive, negative, or neutral."""

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


def classify_all_user_tones(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Classify every user message with rich tone data.

    Returns list of {"tone", "sub_tone", "intensity", "text", "sequence"}
    for use in emotional arc computation.
    """
    try:
        from divineos.core.tone_texture import classify_tone_rich

        use_rich = True
    except Exception:
        use_rich = False

    result: list[dict[str, Any]] = []
    seq = 0
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if not text or len(text) < 3:
            continue
        seq += 1
        if use_rich:
            rich = classify_tone_rich(text)
            result.append(
                {
                    "tone": rich["tone"],
                    "sub_tone": rich["sub_tone"],
                    "intensity": rich["intensity"],
                    "text": text[:200],
                    "sequence": seq,
                }
            )
        else:
            result.append(
                {
                    "tone": _classify_tone(text),
                    "sub_tone": "",
                    "intensity": 0.0,
                    "text": text[:200],
                    "sequence": seq,
                }
            )
    return result


def analyze_tone_shifts(records: list[dict[str, Any]]) -> list[ToneShift]:
    """Track user mood shifts across a session.

    Looks at: message before -> AI action -> message after.
    When tone shifts (positive -> negative), flags the AI action in between.
    """
    shifts: list[ToneShift] = []

    # Build ordered list of user messages with their tones
    # Use rich classification for sub-tone and intensity
    try:
        from divineos.core.tone_texture import classify_tone_rich

        use_rich = True
    except Exception:
        use_rich = False

    user_messages: list[dict[str, Any]] = []
    for r in records:
        if r.get("type") != "user":
            continue
        text = _extract_user_text(r)
        if not text or len(text) < 3:
            continue
        if use_rich:
            rich = classify_tone_rich(text)
            user_messages.append(
                {
                    "text": text,
                    "tone": rich["tone"],
                    "sub_tone": rich["sub_tone"],
                    "intensity": rich["intensity"],
                    "timestamp": r.get("timestamp", ""),
                },
            )
        else:
            user_messages.append(
                {
                    "text": text,
                    "tone": _classify_tone(text),
                    "sub_tone": "",
                    "intensity": 0.0,
                    "timestamp": r.get("timestamp", ""),
                },
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
                new_sub_tone=curr.get("sub_tone", ""),
                new_intensity=curr.get("intensity", 0.0),
            ),
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
        f"during {total_messages} messages.",
    )

    if negative_shifts:
        parts.append(
            f"{len(negative_shifts)} time{'s' if len(negative_shifts) != 1 else ''} "
            f"you went from okay/happy to upset.",
        )
        # Show the worst one
        worst = negative_shifts[0]
        parts.append(
            f"For example, after message {worst.sequence}: "
            f"you were {worst.previous_tone}, then the AI did [{worst.trigger_action[:80]}], "
            f"and you got {worst.new_tone}.",
        )

    if positive_shifts:
        parts.append(
            f"{len(positive_shifts)} time{'s' if len(positive_shifts) != 1 else ''} "
            f"things got better — you went from neutral/upset to happy.",
        )

    parts.append("(Tone tracking is a guess based on your words, not a certainty.)")
    return " ".join(parts)
