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

    Includes completeness tracking so I know when my self-picture is partial.
    """
    sources_available = ["focus", "suppressed", "drivers"]
    sources_succeeded: list[str] = []
    sources_failed: list[str] = []

    focus: list[dict[str, Any]] = []
    try:
        focus = _get_current_focus()
        sources_succeeded.append("focus")
    except _AS_ERRORS as e:
        sources_failed.append("focus")
        logger.debug("Attention focus assembly failed: %s", e)

    suppressed: list[dict[str, Any]] = []
    try:
        suppressed = _get_suppressed()
        sources_succeeded.append("suppressed")
    except _AS_ERRORS as e:
        sources_failed.append("suppressed")
        logger.debug("Attention suppressed assembly failed: %s", e)

    drivers: list[dict[str, Any]] = []
    try:
        drivers = _get_attention_drivers()
        sources_succeeded.append("drivers")
    except _AS_ERRORS as e:
        sources_failed.append("drivers")
        logger.debug("Attention drivers assembly failed: %s", e)

    return {
        "focus": focus,
        "suppressed": suppressed,
        "drivers": drivers,
        "timestamp": time.time(),
        "completeness": {
            "total": len(sources_available),
            "succeeded": len(sources_succeeded),
            "failed": sources_failed,
            "complete": len(sources_failed) == 0,
        },
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
                   FROM system_events
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

    # Self-model gaps — Circuit 2: missing sections surface as focus items.
    # If I can't see part of myself, that gap deserves attention.
    try:
        gaps = _get_self_model_gaps()
        for gap in gaps:
            focus_items.append(
                {
                    "source": "self_model_gap",
                    "content": f"Blind spot: {gap['section']} — {gap['reason']}",
                    "importance": 0.75,
                    "type": "SELF_MODEL",
                    "reason": "incomplete self-knowledge",
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention focus (self-model gaps) failed: %s", e)

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

    # Self-model gaps — Circuit 2: incomplete sections become attention drivers.
    # The system attends to its own blind spots.
    try:
        gaps = _get_self_model_gaps()
        for gap in gaps:
            drivers.append(
                {
                    "driver": "self_model_gap",
                    "description": f"Self-model blind spot: {gap['section']} ({gap['reason']})",
                    "effect": "heightened attention to missing self-knowledge",
                    "strength": gap["strength"],
                }
            )
    except _AS_ERRORS as e:
        logger.debug("Attention drivers (self-model gaps) failed: %s", e)

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


# ─── Circuit 2: Self-Model Gap Detection ──────────────────────────────


# Maps self-model sections to the data sources they depend on.
# If a probe fails, the section is a blind spot.
_SECTION_PROBES: dict[str, tuple[str, str]] = {
    "identity": ("divineos.core.memory", "get_core"),
    "strengths": ("divineos.core.skill_library", "get_strongest_skills"),
    "weaknesses": ("divineos.core.skill_library", "get_weakest_skills"),
    "emotional_baseline": ("divineos.core.affect", "get_session_affect_context"),
    "active_concerns": ("divineos.core.curiosity_engine", "get_open_curiosities"),
    "growth_trajectory": ("divineos.core.drift_detection", "detect_quality_drift"),
    "epistemic_balance": ("divineos.core.epistemic_status", "assess_epistemic_status"),
}


def _get_self_model_gaps() -> list[dict[str, Any]]:
    """Detect self-model blind spots without importing self_model.py.

    Two strategies (fast path first):
    1. Read persisted completeness from last self-model build
    2. Probe data sources directly if no persisted state exists

    Circuit 2: gaps detected here become attention items and drivers.
    The system attends to its own blind spots.
    """
    # Fast path: read persisted completeness (written by self_model.build_self_model)
    try:
        import json
        from pathlib import Path

        path = Path.home() / ".divineos" / "hud" / "self_model_completeness.json"
        if path.exists():
            completeness = json.loads(path.read_text(encoding="utf-8"))
            failed = completeness.get("failed", [])
            if failed:
                return [
                    {
                        "section": section,
                        "reason": "failed in last self-model build",
                        "strength": 0.7,
                    }
                    for section in failed
                ]
            if completeness.get("complete", False):
                return []  # all sections succeeded last time
    except (OSError, json.JSONDecodeError, KeyError):
        pass  # fall through to slow path

    # Slow path: probe data sources directly
    gaps: list[dict[str, Any]] = []

    for section, (module_path, func_name) in _SECTION_PROBES.items():
        try:
            import importlib

            mod = importlib.import_module(module_path)
            func = getattr(mod, func_name)
            result = func()
            # Empty results mean the section has no data
            if not result:
                gaps.append(
                    {
                        "section": section,
                        "reason": "no data available",
                        "strength": 0.5,
                    }
                )
        except _AS_ERRORS:
            gaps.append(
                {
                    "section": section,
                    "reason": "data source unavailable",
                    "strength": 0.7,
                }
            )
        except (ImportError, AttributeError):
            gaps.append(
                {
                    "section": section,
                    "reason": "module not installed",
                    "strength": 0.3,
                }
            )

    return gaps


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
            SESSION_PROFILES,
            detect_session_profile,
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

    # Completeness — do I know what I don't know?
    completeness = schema.get("completeness", {})
    if completeness and not completeness.get("complete", True):
        failed = completeness.get("failed", [])
        succeeded = completeness.get("succeeded", 0)
        total = completeness.get("total", 0)
        lines.append(f"\n# Attention Model Completeness: {succeeded}/{total}")
        lines.append(f"  Missing: {', '.join(failed)}")
        lines.append("  My attention picture is partial right now.")

    return "\n".join(lines) if lines else "No attention data available yet."
