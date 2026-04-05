"""Predictive Session Model — anticipate user needs from session history.

The existing anticipation system matches current context against past
mistakes. This module goes further: it analyzes session history to
predict what the user will likely need next.

Three prediction sources:

1. SEQUENCE PATTERNS: What typically follows the current activity?
   If the last 3 sessions were "build → test → fix bugs", predict
   the next step in the cycle.

2. SESSION PROFILE: What kind of session is this shaping up to be?
   Fast corrections? Deep refactoring? Exploratory research?
   Match against historical session profiles.

3. RECURRING NEEDS: What does the user consistently need at this
   point in a project? (e.g., always asks for tests after new features)
"""

import sqlite3
from typing import Any

from divineos.core.knowledge._base import _get_connection


# ─── Session Profile Detection ─────────────────────────────────────

SESSION_PROFILES = {
    "build": {
        "signals": ["create", "add", "implement", "build", "write", "new file"],
        "typical_next": ["test", "review"],
        "description": "Building new features",
    },
    "fix": {
        "signals": ["fix", "bug", "error", "broken", "fail", "patch"],
        "typical_next": ["test", "verify"],
        "description": "Fixing bugs",
    },
    "refactor": {
        "signals": ["refactor", "clean", "reorganize", "split", "extract", "rename"],
        "typical_next": ["test", "review"],
        "description": "Refactoring code",
    },
    "test": {
        "signals": ["test", "pytest", "assert", "coverage", "verify"],
        "typical_next": ["commit", "build"],
        "description": "Testing",
    },
    "review": {
        "signals": ["audit", "review", "check", "inspect", "examine"],
        "typical_next": ["fix", "refactor"],
        "description": "Reviewing code",
    },
    "explore": {
        "signals": ["research", "explore", "investigate", "understand", "learn"],
        "typical_next": ["build", "plan"],
        "description": "Exploring/researching",
    },
}


def detect_session_profile(events: list[str]) -> dict[str, Any]:
    """Classify the current session into a profile based on events.

    Returns the best matching profile with confidence score.
    """
    if not events:
        return {"profile": "unknown", "confidence": 0.0, "description": "No events yet"}

    combined = " ".join(events).lower()

    best_profile = "unknown"
    best_score = 0.0

    for name, profile in SESSION_PROFILES.items():
        score = 0.0
        for signal in profile["signals"]:
            count = combined.count(signal)
            if count > 0:
                score += min(count * 0.15, 0.5)  # cap per-signal contribution

        if score > best_score:
            best_score = score
            best_profile = name

    if best_score < 0.1:
        return {"profile": "unknown", "confidence": 0.0, "description": "No clear pattern yet"}

    profile_data = SESSION_PROFILES.get(best_profile, {})
    return {
        "profile": best_profile,
        "confidence": min(best_score, 1.0),
        "description": profile_data.get("description", ""),
        "typical_next": profile_data.get("typical_next", []),
    }


# ─── Session History Analysis ──────────────────────────────────────


def get_session_history(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent session summaries from the ledger."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT content, created_at
               FROM events
               WHERE event_type = 'SESSION_END'
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [{"content": r[0], "created_at": r[1]} for r in rows]
    except (sqlite3.OperationalError, OSError, KeyError, TypeError) as e:
        from loguru import logger

        logger.debug("Session history fetch failed: %s", e)
        return []
    finally:
        conn.close()


def detect_recurring_patterns(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Find recurring patterns in session history.

    Looks for activities that appear in 3+ recent sessions.
    """
    if len(history) < 3:
        return []

    # Count activity keywords across sessions
    activity_counts: dict[str, int] = {}
    for session in history:
        content = session.get("content", "").lower()
        seen_this_session: set[str] = set()

        for profile_name, profile in SESSION_PROFILES.items():
            if profile_name in seen_this_session:
                continue
            for signal in profile["signals"]:
                if signal in content:
                    activity_counts[profile_name] = activity_counts.get(profile_name, 0) + 1
                    seen_this_session.add(profile_name)
                    break

    # Patterns appearing in 3+ sessions
    patterns: list[dict[str, Any]] = []
    for activity, count in sorted(activity_counts.items(), key=lambda x: -x[1]):
        if count >= 3:
            profile = SESSION_PROFILES.get(activity, {})
            patterns.append(
                {
                    "activity": activity,
                    "frequency": count,
                    "out_of": len(history),
                    "description": profile.get("description", ""),
                    "typical_next": profile.get("typical_next", []),
                }
            )

    return patterns


# ─── Predictions ───────────────────────────────────────────────────


def predict_session_needs(
    current_events: list[str] | None = None,
    history_limit: int = 10,
) -> dict[str, Any]:
    """Generate predictions for what the user will need.

    Combines current session profile with historical patterns.
    """
    events = current_events or []

    # Current session profile
    profile = detect_session_profile(events)

    # Historical patterns
    history = get_session_history(history_limit)
    recurring = detect_recurring_patterns(history)

    # Build predictions
    predictions: list[dict[str, Any]] = []

    # From current profile — what typically comes next
    if profile["profile"] != "unknown" and profile.get("typical_next"):
        for next_step in profile["typical_next"]:
            next_profile = SESSION_PROFILES.get(next_step, {})
            predictions.append(
                {
                    "prediction": f"After {profile['description'].lower()}, you typically {next_profile.get('description', next_step).lower()}",
                    "source": "session_profile",
                    "confidence": profile["confidence"] * 0.7,
                    "action": next_step,
                }
            )

    # From recurring patterns — what keeps happening
    for pattern in recurring[:3]:
        ratio = pattern["frequency"] / max(pattern["out_of"], 1)
        if ratio >= 0.5:  # appears in 50%+ of sessions
            predictions.append(
                {
                    "prediction": f"{pattern['description']} appears in {pattern['frequency']}/{pattern['out_of']} recent sessions",
                    "source": "recurring_pattern",
                    "confidence": ratio * 0.6,
                    "action": pattern["activity"],
                }
            )

    # Sort by confidence
    predictions.sort(key=lambda p: -p["confidence"])

    return {
        "current_profile": profile,
        "recurring_patterns": recurring,
        "predictions": predictions[:5],  # top 5
        "session_count": len(history),
    }


def format_predictions(result: dict[str, Any]) -> str:
    """Format predictions for display."""
    lines: list[str] = []

    profile = result["current_profile"]
    if profile["profile"] != "unknown":
        lines.append(
            f"Session type: {profile['description']} (confidence: {profile['confidence']:.0%})"
        )

    if result["predictions"]:
        lines.append("\nPredictions:")
        for pred in result["predictions"]:
            conf = pred["confidence"]
            lines.append(f"  → {pred['prediction']} ({conf:.0%})")

    if result["recurring_patterns"]:
        lines.append("\nRecurring patterns:")
        for pat in result["recurring_patterns"]:
            lines.append(f"  • {pat['description']}: {pat['frequency']}/{pat['out_of']} sessions")

    if not lines:
        return "Not enough session history for predictions yet."

    return "\n".join(lines)
