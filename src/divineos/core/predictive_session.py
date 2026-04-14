"""Predictive Session Model — anticipate user needs from session history.

Three prediction sources, from most to least reliable:

1. TRAJECTORY LEARNING: What actually happened in past sessions?
   Track real action sequences (edit -> test -> fail -> edit) and surface
   patterns. "Last 3 times you edited tests/, you ran pytest right after"
   is useful. "You typed 'fix' so try 'test'" is not.

2. SESSION PROFILE: What kind of session is this? Classified from
   actual tool usage patterns, not just keyword matching.

3. RECURRING NEEDS: What does the user consistently do at this
   stage of a project?
"""

import json
import re
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
    """Classify the current session into a profile based on events."""
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
                score += min(count * 0.15, 0.5)

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


# ─── Trajectory Learning ─────────────────────────────────────────

# Action types extracted from tool events
_ACTION_PATTERNS = {
    "read": re.compile(r"read", re.IGNORECASE),
    "edit": re.compile(r"edit|write", re.IGNORECASE),
    "test": re.compile(r"pytest|test", re.IGNORECASE),
    "commit": re.compile(r"git commit|git push", re.IGNORECASE),
    "search": re.compile(r"grep|glob|search|find", re.IGNORECASE),
    "run": re.compile(r"bash|command|run", re.IGNORECASE),
}


def _extract_action_sequence(limit: int = 10) -> list[list[str]]:
    """Extract action sequences from recent sessions.

    Returns a list of sessions, each being a list of action types
    in chronological order.
    """
    conn = _get_connection()
    try:
        # Get session boundaries
        sessions_rows = conn.execute(
            """SELECT created_at FROM system_events
               WHERE event_type = 'SESSION_END'
               ORDER BY created_at DESC LIMIT ?""",
            (limit + 1,),
        ).fetchall()

        if len(sessions_rows) < 2:
            return []

        session_sequences: list[list[str]] = []
        timestamps = [r[0] for r in sessions_rows]

        for i in range(len(timestamps) - 1):
            end_time = timestamps[i]
            start_time = timestamps[i + 1]

            rows = conn.execute(
                """SELECT event_type, payload FROM system_events
                   WHERE timestamp > ? AND timestamp <= ?
                   ORDER BY timestamp ASC""",
                (start_time, end_time),
            ).fetchall()

            actions: list[str] = []
            for event_type, content in rows:
                if event_type != "TOOL_CALL":
                    continue
                content_str = (content or "").lower()

                # Extract tool_name from JSON payload when available
                tool_name = ""
                try:
                    payload = json.loads(content or "")
                    tool_name = (payload.get("tool_name", "") or "").lower()
                except (json.JSONDecodeError, AttributeError):
                    pass

                # Match on parsed tool_name first for accuracy
                matched_action = ""
                if tool_name:
                    for action_name, pattern in _ACTION_PATTERNS.items():
                        if pattern.search(tool_name):
                            matched_action = action_name
                            break
                # Fall back to full content search for unparsed payloads
                if not matched_action:
                    for action_name, pattern in _ACTION_PATTERNS.items():
                        if pattern.search(content_str):
                            matched_action = action_name
                            break
                if matched_action:
                    # Deduplicate consecutive same actions
                    if not actions or actions[-1] != matched_action:
                        actions.append(matched_action)

            if len(actions) >= 2:
                session_sequences.append(actions)

        return session_sequences
    except (sqlite3.OperationalError, OSError):
        return []
    finally:
        conn.close()


def detect_trajectory_patterns(
    sequences: list[list[str]], min_occurrences: int = 2
) -> list[dict[str, Any]]:
    """Find recurring action pairs/triples across session sequences.

    Looks for patterns like "edit -> test" or "edit -> test -> fail -> edit"
    that appear consistently across sessions.
    """
    # Count 2-grams and 3-grams across sessions
    pair_counts: dict[tuple[str, ...], int] = {}
    triple_counts: dict[tuple[str, ...], int] = {}

    for seq in sequences:
        seen_pairs: set[tuple[str, ...]] = set()
        seen_triples: set[tuple[str, ...]] = set()

        for i in range(len(seq) - 1):
            pair = (seq[i], seq[i + 1])
            if pair not in seen_pairs:
                pair_counts[pair] = pair_counts.get(pair, 0) + 1
                seen_pairs.add(pair)

            if i < len(seq) - 2:
                triple = (seq[i], seq[i + 1], seq[i + 2])
                if triple not in seen_triples:
                    triple_counts[triple] = triple_counts.get(triple, 0) + 1
                    seen_triples.add(triple)

    patterns: list[dict[str, Any]] = []
    total = len(sequences)

    # Surface triples first (more specific), then pairs
    for ngram, count in sorted(triple_counts.items(), key=lambda x: -x[1]):
        if count >= min_occurrences:
            patterns.append(
                {
                    "sequence": list(ngram),
                    "frequency": count,
                    "out_of": total,
                    "confidence": count / total,
                    "description": " -> ".join(ngram),
                }
            )

    for ngram, count in sorted(pair_counts.items(), key=lambda x: -x[1]):
        if count >= min_occurrences:
            # Skip pairs already covered by triples
            already_covered = any(
                ngram[0] in p["sequence"] and ngram[1] in p["sequence"] for p in patterns
            )
            if not already_covered:
                patterns.append(
                    {
                        "sequence": list(ngram),
                        "frequency": count,
                        "out_of": total,
                        "confidence": count / total,
                        "description": " -> ".join(ngram),
                    }
                )

    return patterns[:10]


# ─── Session History ──────────────────────────────────────────────


def get_session_history(limit: int = 10) -> list[dict[str, Any]]:
    """Get recent session summaries from the ledger."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT content, created_at
               FROM system_events
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
    """Find recurring activity types in session history."""
    if len(history) < 3:
        return []

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
    """Generate predictions from trajectory learning + profile + recurring patterns."""
    events = current_events or []

    # Current session profile
    profile = detect_session_profile(events)

    # Historical patterns
    history = get_session_history(history_limit)
    recurring = detect_recurring_patterns(history)

    # Trajectory learning — what action sequences actually repeat?
    sequences = _extract_action_sequence(history_limit)
    trajectory_patterns = detect_trajectory_patterns(sequences)

    # Build predictions
    predictions: list[dict[str, Any]] = []

    # From trajectory learning — highest confidence, based on real behavior
    for pattern in trajectory_patterns[:3]:
        seq = pattern["sequence"]
        predictions.append(
            {
                "prediction": f"Recurring workflow: {pattern['description']} ({pattern['frequency']}/{pattern['out_of']} sessions)",
                "source": "trajectory",
                "confidence": pattern["confidence"],
                "action": seq[-1],  # the final action in the sequence
            }
        )

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

    # From recurring patterns
    for pattern in recurring[:3]:
        ratio = pattern["frequency"] / max(pattern["out_of"], 1)
        if ratio >= 0.5:
            predictions.append(
                {
                    "prediction": f"{pattern['description']} appears in {pattern['frequency']}/{pattern['out_of']} recent sessions",
                    "source": "recurring_pattern",
                    "confidence": ratio * 0.6,
                    "action": pattern["activity"],
                }
            )

    predictions.sort(key=lambda p: -p["confidence"])

    return {
        "current_profile": profile,
        "recurring_patterns": recurring,
        "trajectory_patterns": trajectory_patterns,
        "predictions": predictions[:5],
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
            lines.append(f"  -> {pred['prediction']} ({conf:.0%})")

    if result["recurring_patterns"]:
        lines.append("\nRecurring patterns:")
        for pat in result["recurring_patterns"]:
            lines.append(f"  * {pat['description']}: {pat['frequency']}/{pat['out_of']} sessions")

    if not lines:
        return "Not enough session history for predictions yet."

    return "\n".join(lines)
