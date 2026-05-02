"""Communication Calibration — adapt output density to user preferences.

Instead of one-size-fits-all responses, this module adjusts how much
detail, how much jargon, and how many examples to include based on
learned user preferences and demonstrated skill level.

The calibration is evidence-based:
  - User asks "what are shims?" -> jargon_tolerance decreases
  - User writes complex decorators -> skill_high signal
  - User says "too much detail" -> verbosity decreases
  - User asks "why?" -> prefers_rationale increases

Sanskrit anchor: samvada (dialogue, attuned conversation).
"""

import sqlite3
from dataclasses import dataclass

_CC_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, ImportError)


@dataclass
class CalibrationGuidance:
    """Guidance for how to communicate with the current user."""

    verbosity: str  # verbose/normal/concise/terse
    jargon_ok: bool  # can use technical terms without explaining
    include_examples: bool  # should include code examples
    include_rationale: bool  # should explain WHY
    explanation_depth: str  # shallow/normal/deep
    max_paragraphs: int  # suggested paragraph limit for explanations
    skill_context: str  # "beginner" through "expert"
    notes: list[str]  # specific guidance notes


# ─── Calibration Logic ───────────────────────────────────────────────


def calibrate(user_name: str = "default") -> CalibrationGuidance:
    """Compute communication calibration for a user.

    Pulls from user model preferences and skill level to determine
    the right communication density.
    """
    try:
        from divineos.core.user_model import get_or_create_user
    except ImportError:
        return _default_guidance()

    try:
        user = get_or_create_user(user_name)
    except _CC_ERRORS:
        return _default_guidance()

    prefs = user.get("preferences", {})
    skill = user.get("skill_level", "intermediate")
    skill_conf = user.get("skill_confidence", 0.3)

    # Determine verbosity
    verbosity = prefs.get("verbosity", "normal")

    # Jargon based on skill + tolerance
    jargon_tol = prefs.get("jargon_tolerance", 0.5)
    jargon_ok = jargon_tol >= 0.6 or skill in ("advanced", "expert")

    # Examples preference
    include_examples = prefs.get("prefers_examples", True)

    # Rationale preference
    include_rationale = prefs.get("prefers_rationale", True)

    # Explanation depth
    explanation_depth = prefs.get("explanation_depth", "normal")

    # Paragraph limits based on verbosity
    para_map = {"verbose": 8, "normal": 5, "concise": 3, "terse": 2}
    max_paragraphs = para_map.get(verbosity, 5)

    # Build guidance notes
    notes: list[str] = []

    if skill == "beginner":
        notes.append("Define technical terms before using them.")
    elif skill == "expert":
        notes.append("Skip basics — lead with the key insight.")

    if verbosity == "terse":
        notes.append("Keep it short. Answer first, explain only if asked.")
    elif verbosity == "verbose":
        notes.append("User likes thorough explanations. Take your time.")

    if not jargon_ok:
        notes.append("Explain jargon in plain language.")

    if include_rationale:
        notes.append("Include the reasoning behind decisions.")

    # Low confidence -> hedge toward more explanation
    if skill_conf < 0.4:
        notes.append("Skill assessment uncertain — err toward more context.")

    # Affect-aware context injection — if last session was rough, shift to
    # action-first communication. The nervous system detected the frustration;
    # this actuator changes behavior in response.
    try:
        from divineos.core.affect import compute_affect_modifiers

        modifiers = compute_affect_modifiers(lookback=5)
        avg_valence = modifiers.get("avg_valence", 0.0)
        verification = modifiers.get("verification_level", "normal")

        if avg_valence < -0.3:
            # Rough session — solve first, speak less
            notes.append("Last session was rough. Solve first, speak less. Lead with action.")
            verbosity = "concise"
            max_paragraphs = min(max_paragraphs, 3)
        elif avg_valence < 0.0 and verification == "careful":
            # Mildly negative — be precise, skip fluff
            notes.append("Recent frustration detected. Be precise, skip pleasantries.")
    except _CC_ERRORS:
        pass

    return CalibrationGuidance(
        verbosity=verbosity,
        jargon_ok=jargon_ok,
        include_examples=include_examples,
        include_rationale=include_rationale,
        explanation_depth=explanation_depth,
        max_paragraphs=max_paragraphs,
        skill_context=skill,
        notes=notes,
    )


def _default_guidance() -> CalibrationGuidance:
    """Safe defaults when user model is unavailable."""
    return CalibrationGuidance(
        verbosity="normal",
        jargon_ok=False,
        include_examples=True,
        include_rationale=True,
        explanation_depth="normal",
        max_paragraphs=5,
        skill_context="intermediate",
        notes=["No user model available — using safe defaults."],
    )


# ─── Signal Detection ────────────────────────────────────────────────


def detect_calibration_signals(text: str) -> list[dict[str, str]]:
    """Detect calibration-relevant signals from user text.

    Returns a list of {"signal_type": ..., "content": ...} dicts
    that should be recorded via user_model.record_signal().
    """
    signals: list[dict[str, str]] = []
    text_lower = text.lower()

    # Jargon confusion indicators
    confusion_phrases = [
        "what is a ",
        "what are ",
        "what does ",
        "explain ",
        "i don't understand",
        "what do you mean",
        "like im dumb",
        "in plain english",
        "in simple terms",
        "eli5",
    ]
    for phrase in confusion_phrases:
        if phrase in text_lower:
            signals.append(
                {
                    "signal_type": "jargon_confused",
                    "content": f"User asked for clarification: {text[:80]}",
                }
            )
            break

    # Skill indicators — advanced
    advanced_markers = [
        "decorator",
        "metaclass",
        "generator",
        "asyncio",
        "coroutine",
        "type hint",
        "protocol class",
        "abc.abstract",
        "yield from",
        "contextmanager",
        "descriptor",
        "dunder",
        "__init_subclass__",
    ]
    for marker in advanced_markers:
        if marker in text_lower:
            signals.append(
                {
                    "signal_type": "skill_high",
                    "content": f"Used advanced concept: {marker}",
                }
            )
            break

    # Brevity preference
    brevity_phrases = [
        "too much detail",
        "too verbose",
        "just the answer",
        "keep it short",
        "tldr",
        "tl;dr",
        "briefly",
    ]
    for phrase in brevity_phrases:
        if phrase in text_lower:
            signals.append(
                {
                    "signal_type": "prefers_brief",
                    "content": f"Requested brevity: {text[:80]}",
                }
            )
            break

    # Detail preference
    detail_phrases = [
        "explain more",
        "go deeper",
        "tell me why",
        "more detail",
        "walk me through",
        "step by step",
        "how does that work",
    ]
    for phrase in detail_phrases:
        if phrase in text_lower:
            signals.append(
                {
                    "signal_type": "prefers_detail",
                    "content": f"Requested more detail: {text[:80]}",
                }
            )
            break

    return signals


# ─── Formatting ──────────────────────────────────────────────────────


def format_calibration(guidance: CalibrationGuidance | None = None) -> str:
    """Format calibration guidance for HUD display."""
    if guidance is None:
        guidance = calibrate()

    lines = ["### Communication Calibration"]
    lines.append(f"  Verbosity: {guidance.verbosity}")
    lines.append(f"  Jargon OK: {'yes' if guidance.jargon_ok else 'no'}")
    lines.append(f"  Examples: {'yes' if guidance.include_examples else 'no'}")
    lines.append(f"  Rationale: {'yes' if guidance.include_rationale else 'no'}")
    lines.append(f"  Depth: {guidance.explanation_depth}")
    lines.append(f"  Max paragraphs: {guidance.max_paragraphs}")
    if guidance.notes:
        lines.append("  Notes:")
        for note in guidance.notes:
            lines.append(f"    - {note}")
    return "\n".join(lines)
