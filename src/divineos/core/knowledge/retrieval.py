"""Knowledge retrieval — briefing generation, stats, unconsolidated events."""

import json
import time
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _get_connection,
    _row_to_dict,
)
from divineos.core.knowledge.crud import search_knowledge
from divineos.core.knowledge.lessons import get_lesson_summary


def get_unconsolidated_events(limit: int = 100) -> list[dict[str, Any]]:
    """Find events not yet referenced in any knowledge entry's source_events."""
    conn = _get_connection()
    try:
        # Collect all referenced event IDs from knowledge
        rows = conn.execute("SELECT source_events FROM knowledge").fetchall()
        referenced: set[str] = set()
        for row in rows:
            referenced.update(json.loads(row[0]))

        # Get events not in referenced set
        all_events = conn.execute(
            "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events ORDER BY timestamp DESC LIMIT ?",
            (limit + len(referenced),),
        ).fetchall()

        results = []
        for row in all_events:
            if row[0] not in referenced:
                results.append(
                    {
                        "event_id": row[0],
                        "timestamp": row[1],
                        "event_type": row[2],
                        "actor": row[3],
                        "payload": json.loads(row[4]),
                        "content_hash": row[5],
                    },
                )
                if len(results) >= limit:
                    break

        return results
    finally:
        conn.close()


def generate_briefing(
    max_items: int = 20,
    include_types: list[str] | None = None,
    context_hint: str = "",
    deep: bool = False,
    layer: str = "",
) -> str:
    """Generate a structured text briefing for AI session context.

    Layers control what shows up:
      - default: urgent + active layers (focused, actionable)
      - deep=True: urgent + active + stable (full picture)
      - layer="archive": just archived entries (historical)
      - layer="stable": just stable entries
      - layer="all": everything

    Scores knowledge by: confidence * 0.4 + access_frequency * 0.3 + recency * 0.3
    with type-specific decay rates.

    If context_hint is provided, knowledge matching the hint gets a 0.3 score boost.
    Active lessons are always included at the top.
    """
    # Ensure the layer column exists
    try:
        from divineos.core.knowledge.curation import ensure_layer_column

        ensure_layer_column()
    except Exception:
        pass

    conn = _get_connection()
    try:
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND confidence >= 0.2 AND content NOT LIKE '[SUPERSEDED]%'"  # nosec B608
        params: list[Any] = []

        if include_types:
            placeholders = ",".join("?" for _ in include_types)
            query += f" AND knowledge_type IN ({placeholders})"
            params.extend(include_types)

        # Layer filtering
        if layer == "archive":
            # Archive: show regardless of confidence (they were archived, not deleted)
            query = query.replace("AND confidence >= 0.2 ", "")
            query += " AND layer = 'archive'"
        elif layer == "stable":
            query += " AND layer = 'stable'"
        elif layer and layer != "all":
            query += " AND layer = ?"
            params.append(layer)
        elif not layer and not deep:
            # Default: urgent + active only
            query += " AND layer IN ('urgent', 'active')"
        elif deep:
            # Deep: urgent + active + stable (exclude archive)
            query += " AND layer != 'archive'"
        # layer="all" — no filter

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return "No knowledge stored yet."

    # Find which knowledge IDs match the context hint (via FTS5)
    hint_matches: set[str] = set()
    if context_hint:
        try:
            matched = search_knowledge(context_hint, limit=100)
            hint_matches = {m["knowledge_id"] for m in matched}
        except Exception as e:
            logger.warning(
                f"Failed to search knowledge for context hint: {e}",
                exc_info=True,
            )

    entries = [_row_to_dict(row) for row in rows]
    now = time.time()
    max_access = max(e["access_count"] for e in entries) or 1

    # Type-specific half-lives in days
    half_lives = {
        # Sutra-style directives — never decay, always surface
        "DIRECTIVE": None,
        # New types
        "BOUNDARY": 30.0,  # Hard constraints persist
        "PRINCIPLE": 30.0,  # Distilled wisdom persists
        "DIRECTION": None,  # User preferences never decay
        "PROCEDURE": 14.0,  # How-to knowledge
        "FACT": 7.0,
        "OBSERVATION": 3.0,  # Unconfirmed — decay fast
        "EPISODE": 14.0,
        # Legacy types — same decay as their successors
        "MISTAKE": 30.0,
        "PATTERN": 14.0,
        "PREFERENCE": None,
    }

    # Score each entry
    for entry in entries:
        access_score = min(entry["access_count"], max_access) / max_access
        age_days = (now - entry["updated_at"]) / 86400

        half_life = half_lives.get(entry["knowledge_type"], 7.0)
        if half_life is None:
            recency = 1.0  # PREFERENCE: never decays
        else:
            recency = 2 ** (-age_days / half_life)

        score = entry["confidence"] * 0.4 + access_score * 0.3 + recency * 0.3

        # Directives always surface — they're the operating principles
        if entry["knowledge_type"] == "DIRECTIVE":
            score += 1.0

        # Boost if matching context hint
        if entry["knowledge_id"] in hint_matches:
            score += 0.3

        entry["_score"] = score

    # Sort by score, take top items
    entries.sort(key=lambda e: e["_score"], reverse=True)
    entries = entries[:max_items]

    # NOTE: We intentionally do NOT call record_access() here.
    # Briefing display is the system showing entries — not the AI
    # actively querying them. Bumping access_count on every briefing
    # created a feedback loop where popular entries stayed popular
    # regardless of actual usefulness.

    # Get active lessons for the header section
    lessons_text = ""
    try:
        lesson_summary = get_lesson_summary()
        if lesson_summary and "No lessons" not in lesson_summary:
            lessons_text = lesson_summary
    except Exception as e:
        logger.warning(
            f"Failed to retrieve lesson summary: {e}",
            exc_info=True,
        )

    # Group by type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        kt = entry["knowledge_type"]
        grouped.setdefault(kt, []).append(entry)

    # Maturity summary — count across ALL non-superseded entries, not just briefing items
    mat_conn = _get_connection()
    try:
        mat_rows = mat_conn.execute(
            "SELECT maturity, COUNT(*) FROM knowledge "
            "WHERE superseded_by IS NULL AND confidence >= 0.2 "
            "GROUP BY maturity"
        ).fetchall()
        mat_counts = {r[0]: r[1] for r in mat_rows}
    finally:
        mat_conn.close()

    # Find what changed recently (last 24h) for the "what's new" section
    recent_cutoff = now - 86400
    recent_changes: list[dict[str, Any]] = []
    # Check ALL non-superseded entries, not just top-N briefing items
    for entry in [_row_to_dict(row) for row in rows]:
        if entry["updated_at"] < recent_cutoff:
            continue
        mat = entry.get("maturity", "RAW")
        is_new = entry["created_at"] > recent_cutoff
        was_promoted = not is_new and mat != "RAW"
        if is_new and mat != "RAW":
            recent_changes.append(
                {
                    "label": f"NEW {mat}",
                    "type": entry["knowledge_type"],
                    "content": entry["content"].replace("\n", " ")[:100],
                }
            )
        elif was_promoted:
            recent_changes.append(
                {
                    "label": f"PROMOTED {mat}",
                    "type": entry["knowledge_type"],
                    "content": entry["content"].replace("\n", " ")[:100],
                }
            )

    # Format output
    lines = []

    # Handoff note from previous session (one-shot: consumed then cleared)
    try:
        from divineos.core.hud_handoff import clear_handoff_note, load_handoff_note

        handoff = load_handoff_note()
        if handoff:
            lines.append("## Handoff from Last Session\n")
            if handoff.get("summary"):
                lines.append(handoff["summary"])
            if handoff.get("open_threads"):
                lines.append("\n**Open threads:**")
                for thread in handoff["open_threads"]:
                    lines.append(f"  - {thread}")
            if handoff.get("intent"):
                lines.append(f"\n**Intent:** {handoff['intent']}")
            if handoff.get("blockers"):
                lines.append("\n**Blockers:**")
                for blocker in handoff["blockers"]:
                    lines.append(f"  - {blocker}")
            if handoff.get("next_steps"):
                lines.append("\n**Next steps:**")
                for step in handoff["next_steps"]:
                    lines.append(f"  - {step}")
            meta_parts = []
            if handoff.get("mood"):
                meta_parts.append(handoff["mood"])
            if handoff.get("goals_state"):
                meta_parts.append(f"goals: {handoff['goals_state']}")
            snapshot = handoff.get("context_snapshot", {})
            if snapshot.get("session_grade"):
                meta_parts.append(f"grade: {snapshot['session_grade']}")
            if meta_parts:
                lines.append(f"\n*{' | '.join(meta_parts)}*")
            lines.append("\n---\n")
            clear_handoff_note()
    except Exception as e:
        logger.warning(f"Handoff note retrieval failed: {e}")

    lines.append(f"## Session Briefing ({len(entries)} items)\n")

    # Growth trajectory (one-liner from session history)
    try:
        from divineos.core.growth import compute_growth_map

        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            icons = {"improving": "+", "declining": "!", "stable": "~"}
            icon = icons.get(growth["trend"], "~")
            lines.append(
                f"**Growth:** [{icon}] {growth['trend']} over {growth['sessions']} sessions | "
                f"avg score {growth['avg_health_score']:.2f} | "
                f"{growth['lessons']['resolved']} lessons resolved"
            )
            # Tone insight from recent sessions
            tone = growth.get("tone_insight", "")
            if tone:
                lines.append(f"**Tone:** {tone}")
            lines.append("")
    except Exception:
        pass

    # Pattern anticipation — proactive warnings based on context
    if context_hint:
        try:
            from divineos.core.anticipation import anticipate, format_anticipation

            warnings = anticipate(context_hint, max_warnings=3)
            if warnings:
                lines.append(format_anticipation(warnings))
                lines.append("")
        except Exception:
            pass

    # One-line maturity pyramid
    mat_parts = []
    for level in ("CONFIRMED", "TESTED", "HYPOTHESIS", "RAW"):
        count = mat_counts.get(level, 0)
        if count:
            mat_parts.append(f"{count} {level}")
    if mat_parts:
        lines.append(f"**Knowledge:** {' | '.join(mat_parts)}\n")

    # What changed since last session
    if recent_changes:
        lines.append(f"### RECENT CHANGES ({len(recent_changes)})")
        for rc in recent_changes[:5]:
            lines.append(f"- [{rc['label']}] {rc['type']}: {rc['content']}")
        if len(recent_changes) > 5:
            lines.append(f"  ...and {len(recent_changes) - 5} more")
        lines.append("")

    # Logic layer health — surface unwarranted/contradictions
    try:
        from divineos.core.logic.logic_summary import (
            format_logic_health_line,
            get_logic_health_summary,
        )

        logic_stats = get_logic_health_summary()
        logic_line = format_logic_health_line(logic_stats)
        if logic_line:
            lines.append(f"**Logic health:** {logic_line}\n")
    except Exception:
        pass

    if lessons_text:
        lines.append(lessons_text)
        lines.append("")

    for kt in [
        "DIRECTIVE",
        "BOUNDARY",
        "PRINCIPLE",
        "DIRECTION",
        "PROCEDURE",
        "MISTAKE",
        "PREFERENCE",
        "PATTERN",
        "FACT",
        "OBSERVATION",
        "EPISODE",
    ]:
        items = grouped.get(kt, [])
        if not items:
            continue
        plural = {
            "DIRECTIVE": "DIRECTIVES",
            "BOUNDARY": "BOUNDARIES",
            "DIRECTION": "DIRECTIONS",
            "PROCEDURE": "PROCEDURES",
            "EPISODE": "EPISODES",
        }.get(kt, f"{kt}S")
        lines.append(f"### {plural} ({len(items)})")
        for item in items:
            hint_marker = " *" if item["knowledge_id"] in hint_matches else ""
            mat = item.get("maturity", "RAW")
            mat_marker = " ++" if mat == "CONFIRMED" else " +" if mat == "TESTED" else ""
            content = item["content"]
            access = f"({item['access_count']}x accessed)"

            if kt == "DIRECTIVE":
                # Show full chain, access count on its own line
                lines.append(f"- [{item['confidence']:.2f}] {content}{mat_marker}{hint_marker}")
                lines.append(f"  {access}")
            else:
                # Truncate long entries (digests, etc.)
                display = content.replace("\n", " ")
                if len(display) > 150:
                    display = display[:147] + "..."
                lines.append(
                    f"- [{item['confidence']:.2f}] {display} {access}{mat_marker}{hint_marker}"
                )
        lines.append("")

    # Recent journal entries (last 48h)
    try:
        from divineos.core.memory_journal import journal_list

        journal_entries = journal_list(limit=5)
        recent_journal = [j for j in journal_entries if (now - j["created_at"]) < 172800]
        if recent_journal:
            lines.append("### JOURNAL (recent)")
            for j in recent_journal:
                import datetime

                dt = datetime.datetime.fromtimestamp(j["created_at"])
                display = j["content"].replace("\n", " ")
                if len(display) > 120:
                    display = display[:117] + "..."
                lines.append(f"- [{dt:%Y-%m-%d}] {display}")
            lines.append("")
    except Exception as e:
        logger.debug(f"Journal retrieval for briefing failed: {e}")

    # Open questions — things I'm still uncertain about
    try:
        from divineos.core.questions import get_open_questions_summary

        questions_text = get_open_questions_summary(max_items=5)
        if questions_text:
            lines.append(questions_text)
            lines.append("")
    except Exception:
        pass

    return "\n".join(lines)


def knowledge_stats() -> dict[str, Any]:
    """Returns knowledge counts by type, total, and average confidence."""
    conn = _get_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL",
        ).fetchone()[0]

        by_type: dict[str, int] = {}
        for row in conn.execute(
            "SELECT knowledge_type, COUNT(*) FROM knowledge WHERE superseded_by IS NULL GROUP BY knowledge_type",
        ):
            by_type[row[0]] = row[1]

        avg_confidence = 0.0
        if total > 0:
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) FROM knowledge WHERE superseded_by IS NULL",
            ).fetchone()[0]

        most_accessed = []
        for row in conn.execute(
            "SELECT knowledge_id, content, access_count FROM knowledge WHERE superseded_by IS NULL ORDER BY access_count DESC LIMIT 5",
        ):
            most_accessed.append(
                {"knowledge_id": row[0], "content": row[1], "access_count": row[2]},
            )

        return {
            "total": total,
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
            "most_accessed": most_accessed,
        }
    finally:
        conn.close()
