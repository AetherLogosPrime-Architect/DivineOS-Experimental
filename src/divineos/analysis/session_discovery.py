"""Session discovery and aggregation — find, batch-analyze, aggregate."""

from pathlib import Path
from typing import Any

from divineos.analysis.session_analyzer import SessionAnalysis, analyze_session


def find_sessions(search_dir: Path | None = None) -> list[Path]:
    """Find all Claude Code JSONL session files.

    Searches the default .claude directory if no path given.
    Excludes subagent files.
    """
    if search_dir is None:
        search_dir = Path.home() / ".claude" / "projects"

    sessions: list[Path] = []
    if not search_dir.exists():
        return sessions

    for jsonl_file in search_dir.rglob("*.jsonl"):
        if "subagents" in jsonl_file.parts:
            continue
        sessions.append(jsonl_file)

    sessions.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return sessions


def analyze_all_sessions(
    search_dir: Path | None = None,
) -> list[SessionAnalysis]:
    """Find and analyze all available sessions."""
    sessions = find_sessions(search_dir)
    return [analyze_session(s) for s in sessions]


def aggregate_analyses(analyses: list[SessionAnalysis]) -> dict[str, Any]:
    """Combine multiple session analyses into aggregate stats."""
    if not analyses:
        return {"sessions": 0}

    total_corrections = sum(len(a.corrections) for a in analyses)
    total_encouragements = sum(len(a.encouragements) for a in analyses)
    total_decisions = sum(len(a.decisions) for a in analyses)
    total_frustrations = sum(len(a.frustrations) for a in analyses)
    total_preferences = sum(len(a.preferences) for a in analyses)
    total_tool_calls = sum(a.tool_calls_total for a in analyses)
    total_overflows = sum(len(a.context_overflows) for a in analyses)
    total_duration = sum(a.duration_seconds for a in analyses)

    combined_tools: dict[str, int] = {}
    for a in analyses:
        for tool, count in a.tool_usage.items():
            combined_tools[tool] = combined_tools.get(tool, 0) + count

    combined_models: dict[str, int] = {}
    for a in analyses:
        for model, count in a.models_used.items():
            combined_models[model] = combined_models.get(model, 0) + count

    all_corrections: list[str] = []
    for a in analyses:
        all_corrections.extend(c.content[:200] for c in a.corrections)

    all_encouragements: list[str] = []
    for a in analyses:
        all_encouragements.extend(e.content[:200] for e in a.encouragements)

    return {
        "sessions": len(analyses),
        "total_duration_hours": round(total_duration / 3600, 1),
        "total_user_messages": sum(a.user_messages for a in analyses),
        "total_assistant_messages": sum(a.assistant_messages for a in analyses),
        "total_tool_calls": total_tool_calls,
        "total_context_overflows": total_overflows,
        "corrections": total_corrections,
        "encouragements": total_encouragements,
        "decisions": total_decisions,
        "frustrations": total_frustrations,
        "preferences": total_preferences,
        "tool_usage": dict(sorted(combined_tools.items(), key=lambda x: x[1], reverse=True)),
        "models_used": combined_models,
        "correction_texts": all_corrections,
        "encouragement_texts": all_encouragements,
    }
