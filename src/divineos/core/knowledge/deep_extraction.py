"""Deep session extraction — rich knowledge extraction from session records."""

import re
import sqlite3
from typing import Any

from loguru import logger

from divineos.core.knowledge._text import (
    _is_extraction_noise,
    extract_session_topics,
)
from divineos.core.knowledge.extraction import store_knowledge_smart

_DEEP_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)


# Patterns for extracting reasoning context from messages
_REASON_PATTERNS = (
    re.compile(r"\bbecause\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bsince\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bso that\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bthe reason\b\s+(.{10,120})", re.IGNORECASE),
)

_ALTERNATIVE_PATTERNS = (
    re.compile(r"\binstead of\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\brather than\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\bnot\b\s+(\w+.{5,60})", re.IGNORECASE),
)


def _extract_assistant_summary(record: dict[str, Any]) -> str:
    """Extract a short summary of what the assistant was doing in a record."""
    msg = record.get("message", {})
    content = msg.get("content", [])
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            # Take first meaningful sentence
            sentences = re.split(r"[.!?\n]", text)
            for s in sentences:
                s = s.strip()
                if len(s) > 15:
                    parts.append(s[:150])
                    break
        elif block.get("type") == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            if name in ("Read", "Edit", "Write"):
                fp = inp.get("file_path", "")
                parts.append(f"{name} {fp}")
            elif name == "Bash":
                cmd = inp.get("command", "")[:60]
                parts.append(f"Bash: {cmd}")
            else:
                parts.append(f"Tool: {name}")

    return "; ".join(parts[:3])


def _find_reason_in_text(text: str) -> str:
    """Try to extract a reason/justification from text."""
    for pattern in _REASON_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _find_alternative_in_text(text: str) -> str:
    """Try to extract what was rejected/compared against."""
    for pattern in _ALTERNATIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _distill_correction(raw_text: str) -> str:
    """Transform a raw correction quote into a clean, actionable insight.

    The goal is to produce something a future session can act on —
    not a transcript of what the user said.
    """
    text = raw_text.strip()[:300]

    # Strip common prefixes that add noise
    for prefix in (
        "no ",
        "no, ",
        "wrong ",
        "wrong, ",
        "stop ",
        "don't ",
        "thats not ",
        "that's not ",
        "i said ",
        "i meant ",
        "user correction: ",
        "i was corrected: ",
    ):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break

    # Strip casual markers that clutter knowledge
    text = re.sub(r"\.\.+", ".", text)  # ".." -> "."
    text = re.sub(r"\s*:\)+", "", text)  # :) noise
    text = re.sub(r"\s*lol\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bidk\b", "I don't know", text, flags=re.IGNORECASE)
    text = re.sub(r"\bdont\b", "don't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bisnt\b", "isn't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bcant\b", "can't", text, flags=re.IGNORECASE)
    text = re.sub(r"\bwont\b", "won't", text, flags=re.IGNORECASE)

    # Truncate at first long tangent indicator
    for breaker in (" also ", " and also ", " btw ", " anyway "):
        idx = text.lower().find(breaker)
        if idx > 30:  # Only break if we have enough content before it
            text = text[:idx]
            break

    # Clean up whitespace and punctuation
    text = re.sub(r"\s+", " ", text).strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."

    return text


def _classify_user_direction(text: str) -> str:
    """Classify a user direction as PREFERENCE, INSTRUCTION, or DIRECTION.

    PREFERENCE: style/approach choices ("use X", "prefer Y", "I like Z style")
    INSTRUCTION: operational rules ("always X", "never Y", "before doing X, do Y")
    DIRECTION: anything else (general guidance)
    """
    lower = text.lower()
    # Instruction indicators: operational/procedural language
    instruction_starts = (
        "always ",
        "never ",
        "before ",
        "after ",
        "when you ",
        "make sure ",
        "don't forget ",
        "remember to ",
        "run ",
        "check ",
        "test ",
        "verify ",
    )
    if any(lower.startswith(p) for p in instruction_starts):
        return "INSTRUCTION"
    # Preference indicators: style/taste language
    preference_words = (
        "prefer",
        "like to",
        "rather ",
        "style",
        "convention",
        "format",
        "naming",
    )
    if any(p in lower for p in preference_words):
        return "PREFERENCE"
    return "DIRECTION"


# Phrases that indicate encouragement rather than actionable direction.
_ENCOURAGEMENT_PHRASES = (
    "great job",
    "good job",
    "well done",
    "nice work",
    "love it",
    "perfect",
    "exactly right",
    "that's awesome",
    "that's great",
    "fantastic",
    "excellent",
    "brilliant",
    "keep it up",
    "keep going",
    "you're doing great",
    "above and beyond",
    "proud of",
    "amazing work",
    "nailed it",
    "spot on",
)


def _is_encouragement(text: str) -> bool:
    """Return True if text is primarily encouragement/praise, not actionable direction."""
    lower = text.lower()
    # Count encouragement phrase matches
    matches = sum(1 for phrase in _ENCOURAGEMENT_PHRASES if phrase in lower)
    words = text.split()
    # Short text with any encouragement phrase is likely pure praise
    if len(words) < 15 and matches >= 1:
        return True
    # Longer text dominated by encouragement
    if matches >= 2:
        return True
    return False


def _distill_preference(raw_text: str) -> str:
    """Transform a raw preference quote into a clean direction."""
    text = raw_text.strip()[:300]
    # Strip "I want", "I prefer", etc. — rephrase as what I should do
    for prefix in (
        "i want you to ",
        "i want ",
        "i prefer ",
        "i like ",
        "i need you to ",
        "i need ",
        "please ",
        "can you ",
        "could you ",
        "make sure you ",
        "make sure to ",
    ):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break

    # Clean casual markers
    text = re.sub(r"\.\.+", ".", text)
    text = re.sub(r"\s*:\)+", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."
    return text


def _extract_user_text_from_record(record: dict[str, Any]) -> str:
    """Extract clean user text from a record (duplicate of session_analyzer helper)."""
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
    if "<system-reminder>" in content:
        content = content[: content.index("<system-reminder>")]
    return content.strip()


def deep_extract_knowledge(
    analysis: "Any",  # SessionAnalysis — avoid circular import
    records: list[dict[str, Any]],
    affect_confidence_penalty: float = 0.0,
) -> list[str]:
    """Extract rich, structured knowledge from a session analysis + raw records.

    Goes beyond simple signal detection to extract:
    - Correction pairs (what AI did wrong -> what user wanted)
    - User preferences with context
    - Decisions with reasoning and alternatives
    - Session topics

    Args:
        affect_confidence_penalty: If > 0, subtract from all extracted confidence
            values. Applied when session affect was negative — the bar for truth
            gets higher when things aren't going well. Clamped to floor of 0.3.

    Returns list of stored knowledge IDs.
    """
    stored_ids: list[str] = []
    session_id = analysis.session_id
    short_id = session_id[:12]

    def _penalized(base_confidence: float) -> float:
        """Apply affect penalty to confidence, floor at 0.3."""
        if affect_confidence_penalty <= 0:
            return base_confidence
        return max(0.3, base_confidence - affect_confidence_penalty)

    # Build a map of record index -> record for context lookups
    user_indices: list[int] = []
    for i, rec in enumerate(records):
        if rec.get("type") == "user":
            user_indices.append(i)

    # Session topics are extracted but only used as tags on other knowledge,
    # not stored as standalone facts (word frequency alone produces keyword soup).
    topics = extract_session_topics(analysis.user_message_texts)
    topic_tags = [f"topic-{t}" for t in topics[:5]]

    # --- Correction pairs -> PRINCIPLE or BOUNDARY with insight content ---
    for correction in analysis.corrections:
        correction_text = correction.content

        # Skip venting/frustration that matched correction patterns but isn't
        # actionable guidance. Real corrections tell the AI what to do differently;
        # frustrations just express displeasure.
        lower_text = correction_text.lower().strip()
        # Too short to be a real instruction (e.g. "no", "wrong")
        if len(lower_text.split()) < 5:
            continue
        # Frustration indicators without actionable content
        frustration_only = any(
            marker in lower_text
            for marker in (
                "i dont even know",
                "i don't even know",
                "what is going on",
                "fml",
                "im lost",
                "i'm lost",
                "utterly lost",
                "i have no idea",
                "this is a mess",
                "a nightmare",
            )
        )
        if frustration_only:
            continue
        # Find this correction in the raw records and get the assistant message before it
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if not user_text:
                continue
            if user_text[:100] == correction_text[:100]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        # Classify: hard constraint words -> BOUNDARY, otherwise -> PRINCIPLE
        lower = correction_text.lower()
        is_boundary = any(
            w in lower for w in ("never", "always", "must", "don't", "do not", "cannot")
        )
        ktype = "BOUNDARY" if is_boundary else "PRINCIPLE"

        # Store as a clean, actionable insight — not a transcript
        distilled = _distill_correction(correction_text)
        if ai_before:
            # Include what I was doing wrong for context
            content = f"I was {ai_before.lower()}, but the correct approach is: {distilled}"
        else:
            content = distilled

        kid = store_knowledge_smart(
            knowledge_type=ktype,
            content=content,
            confidence=_penalized(0.85),
            source="CORRECTED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "correction-pair", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Preferences -> PREFERENCE/INSTRUCTION/DIRECTION (skip encouragement) ---
    for pref in getattr(analysis, "preferences", []):
        distilled = _distill_preference(pref.content)
        if _is_encouragement(distilled):
            continue
        ktype = _classify_user_direction(distilled)
        kid = store_knowledge_smart(
            knowledge_type=ktype,
            content=distilled,
            confidence=_penalized(0.9),
            source="STATED",
            maturity="CONFIRMED",
            source_events=[session_id],
            tags=["auto-extracted", ktype.lower(), f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Decisions with context ---
    for decision in analysis.decisions:
        decision_text = decision.content
        # Skip short affirmations that aren't real decisions
        if len(decision_text.split()) < 8:
            continue
        # Skip if the noise filter catches it
        if _is_extraction_noise(f"I decided: {decision_text}", "PRINCIPLE"):
            continue
        reason = _find_reason_in_text(decision_text)
        alternative = _find_alternative_in_text(decision_text)

        # Also check the next user message for reasoning
        if not reason:
            for i, rec in enumerate(records):
                if rec.get("type") != "user":
                    continue
                user_text = _extract_user_text_from_record(rec)
                if user_text and user_text[:80] == decision_text[:80]:
                    # Check next user message for reasoning
                    for j in range(i + 1, min(i + 4, len(records))):
                        if records[j].get("type") == "user":
                            next_text = _extract_user_text_from_record(records[j])
                            reason = _find_reason_in_text(next_text)
                            break
                    break

        parts = [f"I decided: {decision_text[:200]}"]
        if alternative:
            parts.append(f"I considered but rejected: {alternative}")
        if reason:
            parts.append(f"Because: {reason}")

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=". ".join(parts),
            confidence=_penalized(0.9),
            source="DEMONSTRATED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "decision", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Encouragements as positive patterns ---
    for enc in analysis.encouragements:
        # Find what the AI did right (assistant message before encouragement)
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if user_text and user_text[:80] == enc.content[:80]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        if not ai_before:
            # Without knowing what the AI did right, the encouragement is just
            # a raw user quote with no actionable insight. Skip it.
            continue

        # Don't include raw user quote — just capture what I did right
        content = f"I {ai_before.lower()} and the user confirmed this was the right approach."

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=content,
            confidence=_penalized(0.9),
            source="DEMONSTRATED",
            maturity="TESTED",
            source_events=[session_id],
            tags=["auto-extracted", "encouragement", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Structural edges: link extracted knowledge by how it was created ---
    # These are high-confidence edges because the relationship is known from
    # extraction context, not inferred from word overlap.
    try:
        _create_structural_edges(stored_ids)
    except _DEEP_ERRORS as e:
        logger.debug(f"Structural edge creation failed: {e}", exc_info=True)

    return stored_ids


def _create_structural_edges(stored_ids: list[str]) -> int:
    """Create edges between extracted entries based on their types and tags.

    Returns number of edges created.
    """
    if len(stored_ids) < 2:
        return 0

    from divineos.core.knowledge._base import _get_connection
    from divineos.core.knowledge.edges import create_edge

    conn = _get_connection()
    try:
        valid_ids = [sid for sid in stored_ids if sid]
        if not valid_ids:
            return 0

        placeholders = ",".join("?" for _ in valid_ids)
        rows = conn.execute(
            f"SELECT knowledge_id, knowledge_type, tags FROM knowledge "  # nosec B608
            f"WHERE knowledge_id IN ({placeholders})",
            valid_ids,
        ).fetchall()
    finally:
        conn.close()

    entries = {r[0]: {"type": r[1], "tags": r[2] or ""} for r in rows}
    created = 0

    # Group by extraction origin
    corrections = [k for k, v in entries.items() if "correction-pair" in v["tags"]]
    encouragements = [k for k, v in entries.items() if "encouragement" in v["tags"]]
    decisions = [k for k, v in entries.items() if "decision" in v["tags"]]
    preferences = [
        k
        for k, v in entries.items()
        if any(t in v["tags"] for t in ("preference", "instruction", "direction"))
    ]

    # Cap list sizes to prevent O(n²) explosion on marathon sessions.
    # Past the first ~20 corrections, additional cross-links add noise not signal.
    _MAX_CROSS_LINK = 20
    corrections = corrections[:_MAX_CROSS_LINK]
    encouragements = encouragements[:_MAX_CROSS_LINK]
    decisions = decisions[:_MAX_CROSS_LINK]
    preferences = preferences[:_MAX_CROSS_LINK]

    # Corrections CAUSED_BY the same session context -> link them
    for i, cid_a in enumerate(corrections):
        for cid_b in corrections[i + 1 :]:
            try:
                create_edge(cid_a, cid_b, "RELATED_TO", notes="auto: co-extracted corrections")
                created += 1
            except _DEEP_ERRORS:
                pass

    # Encouragements SUPPORTS decisions from same session
    for eid in encouragements:
        for did in decisions:
            try:
                create_edge(eid, did, "SUPPORTS", notes="auto: encouragement supports decision")
                created += 1
            except _DEEP_ERRORS:
                pass

    # Preferences APPLIES_TO corrections (user direction shapes future behavior)
    for pid in preferences:
        for cid in corrections:
            try:
                create_edge(pid, cid, "APPLIES_TO", notes="auto: preference applies to correction")
                created += 1
            except _DEEP_ERRORS:
                pass

    # Decisions DERIVED_FROM corrections (decisions often respond to problems)
    for did in decisions:
        for cid in corrections:
            try:
                create_edge(did, cid, "DERIVED_FROM", notes="auto: decision from correction")
                created += 1
            except _DEEP_ERRORS:
                pass

    if created:
        logger.debug(f"Created {created} structural edges from {len(entries)} extracted entries")

    return created
