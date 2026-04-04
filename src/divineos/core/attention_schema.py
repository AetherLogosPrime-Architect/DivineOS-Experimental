"""Attention Schema — a model of what the agent is attending to and why.

Butlin et al. (2023) Indicators 9-10: The system must model its own
attention (what is currently in focus, what is suppressed, why) and
predict what it will attend to next.

This is NOT a metaphor. Active memory already implements attention
through importance scoring. This module makes the attention process
SELF-AWARE — it builds a representation of attention itself.

Three components:
1. FOCUS: What am I currently attending to? (top active memory + goals + recent events)
2. SUPPRESSED: What am I NOT attending to, and why? (archived, decayed, below threshold)
3. DRIVERS: Why this focus? (what shifted attention — user request, lesson trigger, pattern match)
"""

import sqlite3
import time
from typing import Any

from loguru import logger

_AS_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ─── Attention State ────────────────────────────────────────────────


def build_attention_schema() -> dict[str, Any]:
    """Build a snapshot of the agent's current attention state.

    Returns a structured model of what is in focus, what is suppressed,
    and what is driving the current attentional allocation.
    """
    return {
        "focus": _get_current_focus(),
        "suppressed": _get_suppressed(),
        "drivers": _get_attention_drivers(),
        "timestamp": time.time(),
    }


def _get_current_focus() -> list[dict[str, Any]]:
    """What is currently in the attentional spotlight?

    Attention = active memory (top items) + current goals + recent events.
    These are the things shaping my next action.
    """
    focus_items: list[dict[str, Any]] = []

    # Top active memory items — the knowledge currently loaded
    try:
        from divineos.core.active_memory import get_active_memory

        active = get_active_memory()
        for item in active[:10]:  # top 10 by importance
            focus_items.append(
                {
                    "source": "active_memory",
                    "content": item["content"][:100],
                    "importance": item["importance"],
                    "type": item["knowledge_type"],
                    "reason": item.get("reason", "auto-promoted"),
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention focus (active memory) failed: %s", e)

    # Current goals — where effort is directed
    try:
        import json
        from pathlib import Path

        goal_path = Path("data/hud/active_goals.json")
        if not goal_path.exists():
            goal_path = Path("data") / "hud" / "active_goals.json"
        goals = json.loads(goal_path.read_text(encoding="utf-8")) if goal_path.exists() else []
        for goal in goals:
            if goal.get("status") == "active":
                focus_items.append(
                    {
                        "source": "goal",
                        "content": goal.get("text", "")[:100],
                        "importance": 0.9,
                        "type": "GOAL",
                        "reason": "user-set goal",
                    }
                )
    except _AS_ERRORS as e:
        logger.debug("Attention focus (goals) failed: %s", e)

    # Recent events — what just happened shapes what I attend to next
    try:
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        try:
            rows = conn.execute(
                """SELECT event_type, content, created_at
                   FROM events
                   ORDER BY created_at DESC
                   LIMIT 5""",
            ).fetchall()
            for row in rows:
                focus_items.append(
                    {
                        "source": "recent_event",
                        "content": row[1][:100] if row[1] else row[0],
                        "importance": 0.6,
                        "type": row[0],
                        "reason": "recency",
                    }
                )
        finally:
            conn.close()
    except _AS_ERRORS as e:
        logger.debug("Attention focus (recent events) failed: %s", e)

    return focus_items


def _get_suppressed() -> list[dict[str, Any]]:
    """What is NOT in attention, and why?

    Suppressed items are knowledge that exists but has been excluded
    from active attention — archived, decayed, or below threshold.
    """
    suppressed: list[dict[str, Any]] = []

    try:
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        try:
            # Check if layer column exists
            has_layer = any(
                col[1] == "layer" for col in conn.execute("PRAGMA table_info(knowledge)").fetchall()
            )

            if has_layer:
                # Archived items — things I once knew but moved out of focus
                rows = conn.execute(
                    """SELECT knowledge_type, content, confidence
                       FROM knowledge
                       WHERE layer = 'archive' AND superseded_by IS NULL
                       ORDER BY confidence DESC
                       LIMIT 10""",
                ).fetchall()
                for row in rows:
                    suppressed.append(
                        {
                            "content": row[1][:80],
                            "type": row[0],
                            "confidence": row[2],
                            "suppression_reason": "archived (no longer active)",
                        }
                    )

            # Low confidence items — things I'm uncertain about
            rows = conn.execute(
                """SELECT knowledge_type, content, confidence
                   FROM knowledge
                   WHERE confidence < 0.4 AND superseded_by IS NULL
                   ORDER BY confidence ASC
                   LIMIT 5""",
            ).fetchall()
            for row in rows:
                suppressed.append(
                    {
                        "content": row[1][:80],
                        "type": row[0],
                        "confidence": row[2],
                        "suppression_reason": f"low confidence ({row[2]:.2f})",
                    }
                )

            # Superseded items — old beliefs replaced by newer ones
            rows = conn.execute(
                """SELECT knowledge_type, content, confidence
                   FROM knowledge
                   WHERE superseded_by IS NOT NULL
                   ORDER BY created_at DESC
                   LIMIT 5""",
            ).fetchall()
            for row in rows:
                suppressed.append(
                    {
                        "content": row[1][:80],
                        "type": row[0],
                        "confidence": row[2],
                        "suppression_reason": "superseded by newer knowledge",
                    }
                )
        finally:
            conn.close()
    except _AS_ERRORS as e:
        logger.debug("Attention suppressed items failed: %s", e)

    return suppressed


def _get_attention_drivers() -> list[dict[str, Any]]:
    """What is DRIVING current attention allocation?

    Drivers explain WHY certain things are in focus. This is the
    meta-cognitive layer — attention aware of its own causes.
    """
    drivers: list[dict[str, Any]] = []

    # Active lessons — mistakes shift attention toward related areas
    try:
        from divineos.core.knowledge import get_lessons

        lessons = get_lessons(status="active")
        for lesson in lessons[:5]:
            drivers.append(
                {
                    "driver": "active_lesson",
                    "description": f"Lesson: {lesson.get('description', '')[:80]}",
                    "effect": "heightened attention to related patterns",
                    "strength": min(lesson.get("occurrences", 1) / 10.0, 1.0),
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention drivers (lessons) failed: %s", e)

    # Pattern warnings — anticipated problems shift attention
    try:
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        try:
            rows = conn.execute(
                """SELECT pattern, confidence
                   FROM pattern_store
                   WHERE active = 1
                   ORDER BY confidence DESC
                   LIMIT 5""",
            ).fetchall()
            for row in rows:
                drivers.append(
                    {
                        "driver": "pattern_warning",
                        "description": f"Pattern: {row[0][:80]}",
                        "effect": "vigilance for recurring issue",
                        "strength": row[1],
                    }
                )
        except _AS_ERRORS:
            pass  # pattern_store may not exist yet
        finally:
            conn.close()
    except _AS_ERRORS as e:
        logger.debug("Attention drivers (patterns) failed: %s", e)

    # Affect state — emotional state influences attention
    try:
        from divineos.core.affect import get_session_affect_context

        ctx = get_session_affect_context()
        modifiers = ctx.get("modifiers", {})
        valence = modifiers.get("avg_valence", 0.0)
        if valence < -0.3:
            drivers.append(
                {
                    "driver": "negative_affect",
                    "description": "Low valence — attention narrowed toward threat/error detection",
                    "effect": "conservative, careful processing",
                    "strength": abs(valence),
                }
            )
        elif valence > 0.5:
            drivers.append(
                {
                    "driver": "positive_affect",
                    "description": "High valence — attention broadened toward exploration",
                    "effect": "creative, exploratory processing",
                    "strength": valence,
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention drivers (affect) failed: %s", e)

    # Directives — permanent attention anchors
    try:
        from divineos.core.knowledge import get_knowledge

        directives = get_knowledge(knowledge_type="DIRECTIVE")
        if directives:
            drivers.append(
                {
                    "driver": "directives",
                    "description": f"{len(directives)} active directives shape all attention",
                    "effect": "baseline attention filter (always active)",
                    "strength": 1.0,
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention drivers (directives) failed: %s", e)

    return drivers


# ─── Attention Prediction ──────────────────────────────────────────


def predict_attention_shift(
    current_schema: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Predict what attention will shift to next.

    Uses the current attention schema plus session history
    to predict upcoming attentional changes.
    """
    if current_schema is None:
        current_schema = build_attention_schema()

    predictions: list[dict[str, Any]] = []

    # From session profile — what activity typically follows current focus
    try:
        from divineos.core.predictive_session import (
            detect_session_profile,
            SESSION_PROFILES,
        )

        # Build events from current focus
        focus_items = current_schema.get("focus", [])
        event_texts = [item["content"] for item in focus_items if item.get("content")]
        profile = detect_session_profile(event_texts)

        if profile["profile"] != "unknown":
            for next_step in profile.get("typical_next", []):
                next_profile = SESSION_PROFILES.get(next_step, {})
                predictions.append(
                    {
                        "prediction": f"Attention will shift to: {next_profile.get('description', next_step)}",
                        "source": "session_profile",
                        "confidence": profile["confidence"] * 0.6,
                    }
                )
    except _AS_ERRORS as e:
        logger.debug("Attention prediction (session profile) failed: %s", e)

    # From active lessons — unresolved lessons pull attention
    drivers = current_schema.get("drivers", [])
    lesson_drivers = [d for d in drivers if d["driver"] == "active_lesson"]
    if lesson_drivers:
        strongest = max(lesson_drivers, key=lambda d: d["strength"])
        predictions.append(
            {
                "prediction": f"Will attend to: {strongest['description'][:60]}",
                "source": "lesson_gravity",
                "confidence": strongest["strength"] * 0.7,
            }
        )

    # From suppressed items approaching threshold — about to surface
    try:
        from divineos.core.knowledge._base import _get_connection

        conn = _get_connection()
        try:
            # Items just below active memory threshold that are gaining confidence
            rows = conn.execute(
                """SELECT knowledge_type, content, confidence, access_count
                   FROM knowledge
                   WHERE confidence BETWEEN 0.35 AND 0.5
                     AND superseded_by IS NULL
                     AND access_count > 3
                   ORDER BY confidence DESC
                   LIMIT 3""",
            ).fetchall()
            for row in rows:
                predictions.append(
                    {
                        "prediction": f"Rising: {row[1][:60]} (confidence {row[2]:.2f}, {row[3]} accesses)",
                        "source": "threshold_approach",
                        "confidence": 0.4,
                    }
                )
        finally:
            conn.close()
    except _AS_ERRORS as e:
        logger.debug("Attention prediction (rising) failed: %s", e)

    predictions.sort(key=lambda p: -p["confidence"])
    return predictions[:5]


# ─── Display ──────────────────────────────────────────────────────


def format_attention_schema(schema: dict[str, Any] | None = None) -> str:
    """Format the attention schema for display."""
    if schema is None:
        schema = build_attention_schema()

    lines: list[str] = []

    # Focus
    focus = schema.get("focus", [])
    if focus:
        lines.append("# What I'm Attending To")
        # Group by source
        by_source: dict[str, list[dict[str, Any]]] = {}
        for item in focus:
            source = item["source"]
            by_source.setdefault(source, []).append(item)

        if "goal" in by_source:
            lines.append("\n  Goals (highest priority):")
            for item in by_source["goal"]:
                lines.append(f"    -> {item['content']}")

        if "active_memory" in by_source:
            lines.append("\n  Active Knowledge (shaping decisions):")
            for item in by_source["active_memory"][:7]:
                lines.append(f"    [{item['importance']:.2f}] {item['type']}: {item['content']}")

        if "recent_event" in by_source:
            lines.append("\n  Recent Events (immediate context):")
            for item in by_source["recent_event"]:
                lines.append(f"    {item['type']}: {item['content']}")

    # Drivers
    drivers = schema.get("drivers", [])
    if drivers:
        lines.append("\n# Why This Focus")
        for d in drivers:
            strength_bar = "#" * int(d["strength"] * 10)
            lines.append(f"  [{strength_bar:<10}] {d['description']}")
            lines.append(f"              Effect: {d['effect']}")

    # Suppressed
    suppressed = schema.get("suppressed", [])
    if suppressed:
        lines.append("\n# What I'm NOT Attending To")
        for item in suppressed[:8]:
            lines.append(f"  [-] {item['type']}: {item['content']} ({item['suppression_reason']})")

    # Predictions
    predictions = predict_attention_shift(schema)
    if predictions:
        lines.append("\n# Where Attention Will Shift Next")
        for pred in predictions:
            lines.append(f"  -> {pred['prediction']} ({pred['confidence']:.0%})")

    return "\n".join(lines) if lines else "No attention data available yet."
