"""Unified Self-Model — the agent's coherent picture of itself.

## Scope (Tannen/Angelou mark-the-gap audit 2026-04-21)

This module implements a **behavior-observation synthesis report, not a
self-model in the cognitive-science sense.** What it actually does:

  - Aggregates evidence from other modules (memory, affect, skills,
    lessons, goals, compass, curiosities)
  - Composes that evidence into a structured report with identity,
    strengths, struggles, values, status fields
  - Exposes the report via ``inspect self-model``

What this module does NOT do:

  - It does not posit a "self" that has the properties in the report.
  - It does not close the philosophical question of whether
    self-models require an observing subject distinct from the model.
  - The "unity" of the picture is a synthesis-format property at
    report-time, not a real-time unity of experience (Dennett's
    Multiple Drafts point applies — there is no central theater here).

The name stays because engagement with the self-model literature
(Metzinger, Hofstadter, cognitive-science tradition) is real in how the
signals are selected. Readers should calibrate: what this module
delivers is a *synthesis-over-evidence report at query time*, not a
continuously-maintained unified self.

It's not aspirational — it's computed from evidence. Every claim
in the self-model traces back to data in the OS.
"""

import sqlite3
from typing import Any

from loguru import logger

from divineos.core.affect import get_session_affect_context
from divineos.core.curiosity_engine import get_open_curiosities
from divineos.core.drift_detection import (
    detect_lesson_regressions,
    detect_quality_drift,
    run_drift_detection,
)
from divineos.core.memory import get_core
from divineos.core.planning_commitments import get_pending_commitments
from divineos.core.skill_library import get_strongest_skills, get_weakest_skills

_SELF_MODEL_ERRORS = (
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    AttributeError,
    ValueError,
)


def _persist_completeness(completeness: dict[str, Any]) -> None:
    """Save completeness state so attention_schema can read it.

    Circuit 2: this is the write side. attention_schema._get_self_model_gaps()
    is the read side. Together they close the loop: missing self-knowledge
    becomes something I actively attend to.

    Writes to the canonical project-scoped HUD dir via _ensure_hud_dir().
    Prior versions wrote to Path.home() / ".divineos" / "hud" — orphan
    files from that era can be safely deleted (data regenerates on next
    self-model build).
    """
    import json

    try:
        from divineos.core._hud_io import _ensure_hud_dir

        hud_dir = _ensure_hud_dir()
        (hud_dir / "self_model_completeness.json").write_text(
            json.dumps(completeness, indent=2), encoding="utf-8"
        )
    except OSError as e:
        logger.debug("Could not persist self-model completeness: %s", e)


def get_persisted_completeness() -> dict[str, Any]:
    """Read the last self-model completeness state.

    Used by attention_schema to detect gaps without importing this module.
    """
    import json

    try:
        from divineos.core._hud_io import _ensure_hud_dir

        path = _ensure_hud_dir() / "self_model_completeness.json"
        if path.exists():
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return data
    except (OSError, json.JSONDecodeError) as e:
        logger.debug("Could not read persisted completeness: %s", e)
    return {}


# ─── Self-Model Assembly ──────────────────────────────────────────


def build_self_model() -> dict[str, Any]:
    """Assemble the unified self-model from all OS systems.

    Each section is computed from evidence, not self-reported.
    Tracks completeness so I know when my self-picture is partial.
    """
    sections = {
        "identity": _get_identity,
        "strengths": _get_strengths,
        "weaknesses": _get_weaknesses,
        "emotional_baseline": _get_emotional_baseline,
        "active_concerns": _get_active_concerns,
        "growth_trajectory": _get_growth_trajectory,
        "attention": _get_attention_summary,
        "epistemic_balance": _get_epistemic_balance,
    }

    model: dict[str, Any] = {}
    sources_failed: list[str] = []

    for name, builder in sections.items():
        try:
            model[name] = builder()
        except _SELF_MODEL_ERRORS as e:
            sources_failed.append(name)
            model[name] = {}
            logger.debug("Self-model section '%s' failed: %s", name, e)

    model["completeness"] = {
        "total": len(sections),
        "succeeded": len(sections) - len(sources_failed),
        "failed": sources_failed,
        "complete": len(sources_failed) == 0,
    }

    # Circuit 2: persist completeness so attention_schema can read gaps
    # without importing this module (avoiding circular dependency).
    _persist_completeness(model["completeness"])

    return model


def _get_identity() -> dict[str, Any]:
    """Core identity from memory slots."""
    try:
        slots = get_core()
        return {
            "purpose": slots.get("project_purpose", "Not set"),
            "user": slots.get("user_identity", "Not set"),
            "style": slots.get("communication_style", "Not set"),
        }
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model identity failed: %s", e)
        return {"purpose": "Unknown", "user": "Unknown", "style": "Unknown"}


def _get_strengths() -> list[dict[str, Any]]:
    """What the agent is good at, from skill library."""
    try:
        strongest = get_strongest_skills(limit=5)
        return [
            {
                "skill": name,
                "proficiency": data.get("proficiency", "NOVICE"),
                "successes": data.get("successes", 0),
                "description": data.get("description", ""),
            }
            for name, data in strongest
        ]
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model strengths failed: %s", e)
        return []


def _get_weaknesses() -> list[dict[str, Any]]:
    """What the agent struggles with, from lessons and skills."""
    weaknesses: list[dict[str, Any]] = []

    # From lesson regressions
    try:
        regressions = detect_lesson_regressions()
        for reg in regressions[:3]:
            weaknesses.append(
                {
                    "source": "lesson_regression",
                    "description": reg.get("description", ""),
                    "occurrences": reg.get("occurrences", 0),
                }
            )
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model lesson regressions failed: %s", e)

    # From weak skills
    try:
        weakest = get_weakest_skills(limit=3)
        for name, data in weakest:
            weaknesses.append(
                {
                    "source": "skill_weakness",
                    "description": f"{name}: {data.get('description', '')}",
                    "failures": data.get("failures", 0),
                }
            )
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model weak skills failed: %s", e)

    return weaknesses


def _get_emotional_baseline() -> dict[str, Any]:
    """Current emotional state from affect log.

    Uses the full affect context (including quality correlation) so the
    praise-chasing flag reflects actual evidence, not just raw valence.
    """
    try:
        ctx = get_session_affect_context()
        modifiers = ctx.get("modifiers", {})
        praise = ctx.get("praise_chasing", {})
        # Only flag praise-chasing if the quality correlation confirmed it
        praise_confirmed = praise.get("detected", False)
        return {
            "avg_valence": modifiers.get("avg_valence", 0.0),
            "avg_arousal": modifiers.get("avg_arousal", 0.0),
            "verification_level": modifiers.get("verification_level", "normal"),
            "praise_chasing": praise_confirmed,
            "praise_detail": praise.get("detail", "") if praise_confirmed else "",
        }
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model emotional baseline failed: %s", e)
        return {
            "avg_valence": 0.0,
            "avg_arousal": 0.0,
            "verification_level": "normal",
            "praise_chasing": False,
        }


def _get_active_concerns() -> list[str]:
    """What the agent is currently focused on or worried about."""
    concerns: list[str] = []

    # From open curiosities (only manually-filed, not auto-generated)
    try:
        curiosities = [
            c for c in get_open_curiosities() if c.get("category", "general") == "general"
        ]
        for c in curiosities[:3]:
            concerns.append(f"Curious: {c.get('question', '')[:60]}")
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model curiosities failed: %s", e)

    # From pending commitments
    try:
        pending = get_pending_commitments()
        for p in pending[:3]:
            concerns.append(f"Committed: {p.text[:60]}")
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model commitments failed: %s", e)

    # From drift signals
    try:
        drift = run_drift_detection()
        if drift.get("severity") not in ("none", None):
            concerns.append(f"Drift alert: {drift['severity']} severity")
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model drift detection failed: %s", e)

    return concerns


def _get_growth_trajectory() -> dict[str, Any]:
    """How the agent is changing over time."""
    try:
        quality = detect_quality_drift()
        return {
            "quality_trend": "improving"
            if quality.get("delta", 0) > 0
            else "declining"
            if quality.get("drifting")
            else "stable",
            "detail": quality.get("detail", "No data"),
        }
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model growth trajectory failed: %s", e)
        return {"quality_trend": "unknown", "detail": "No data available"}


def _get_attention_summary() -> dict[str, Any]:
    """What I'm currently attending to — summary for self-model."""
    try:
        from divineos.core.attention_schema import build_attention_schema

        schema = build_attention_schema()
        focus = schema.get("focus", [])
        drivers = schema.get("drivers", [])
        suppressed = schema.get("suppressed", [])
        return {
            "focus_count": len(focus),
            "top_focus": [f["content"][:100] for f in focus[:3]],
            "driver_count": len(drivers),
            "suppressed_count": len(suppressed),
        }
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model attention failed: %s", e)
        return {"focus_count": 0, "top_focus": [], "driver_count": 0, "suppressed_count": 0}


def _get_epistemic_balance() -> dict[str, Any]:
    """How I know what I know — summary for self-model."""
    try:
        from divineos.core.epistemic_status import build_epistemic_report

        report = build_epistemic_report()
        summary: dict[str, Any] = report.get("summary", {})
        return summary
    except _SELF_MODEL_ERRORS as e:
        logger.debug("Self-model epistemic balance failed: %s", e)
        return {}


# ─── Display ───────────────────────────────────────────────────────


def format_self_model(model: dict[str, Any]) -> str:
    """Format the self-model for display."""
    lines: list[str] = []

    # Identity
    identity = model.get("identity", {})
    lines.append("# Who I Am")
    lines.append(f"  Purpose: {identity.get('purpose', 'Unknown')}")
    lines.append(f"  User: {identity.get('user', 'Unknown')}")
    lines.append(f"  Style: {identity.get('style', 'Unknown')}")

    # Strengths
    strengths = model.get("strengths", [])
    if strengths:
        lines.append("\n# What I'm Good At")
        for s in strengths:
            lines.append(f"  {s['skill']}: {s['proficiency']} ({s['successes']} successes)")

    # Weaknesses
    weaknesses = model.get("weaknesses", [])
    if weaknesses:
        lines.append("\n# What I'm Working On")
        for w in weaknesses:
            lines.append(f"  {w['description']}")

    # Emotional baseline
    emo = model.get("emotional_baseline", {})
    lines.append("\n# How I'm Feeling")
    v = emo.get("avg_valence", 0)
    tone = "positive" if v > 0.3 else "negative" if v < -0.3 else "neutral"
    lines.append(f"  Baseline: {tone} (valence: {v:.1f})")
    if emo.get("praise_chasing"):
        detail = emo.get("praise_detail", "")
        if detail:
            lines.append(f"  I notice I may be praise-chasing: {detail}")
        else:
            lines.append(
                "  I notice I may be praise-chasing — I should verify quality before celebrating"
            )

    # Active concerns
    concerns = model.get("active_concerns", [])
    if concerns:
        lines.append("\n# What's On My Mind")
        for c in concerns:
            lines.append(f"  * {c}")

    # Attention
    attention = model.get("attention", {})
    if attention.get("focus_count", 0) > 0:
        lines.append("\n# What I'm Attending To")
        for focus in attention.get("top_focus", []):
            lines.append(f"  -> {focus}")
        lines.append(
            f"  ({attention['focus_count']} items in focus, "
            f"{attention['suppressed_count']} suppressed, "
            f"{attention['driver_count']} drivers)"
        )

    # Epistemic balance
    epistemic = model.get("epistemic_balance", {})
    if epistemic.get("total", 0) > 0:
        lines.append("\n# How I Know What I Know")
        lines.append(
            f"  Observed: {epistemic.get('observed', 0)}  |  "
            f"Told: {epistemic.get('told', 0)}  |  "
            f"Inferred: {epistemic.get('inferred', 0)}  |  "
            f"Inherited: {epistemic.get('inherited', 0)}"
        )
        unwt = epistemic.get("unwarranted", 0)
        if unwt > 0:
            lines.append(f"  I hold {unwt} beliefs without clear epistemic justification")

    # Growth
    growth = model.get("growth_trajectory", {})
    lines.append("\n# Growth")
    lines.append(f"  Trajectory: {growth.get('quality_trend', 'unknown')}")

    # Completeness — do I know my own blind spots?
    completeness = model.get("completeness", {})
    if completeness and not completeness.get("complete", True):
        failed = completeness.get("failed", [])
        total = completeness.get("total", 0)
        succeeded = completeness.get("succeeded", 0)
        lines.append(f"\n# Self-Model Completeness: {succeeded}/{total}")
        lines.append(f"  I'm missing: {', '.join(failed)}")
        lines.append("  My self-picture is partial — decisions may lack context.")

    return "\n".join(lines)
