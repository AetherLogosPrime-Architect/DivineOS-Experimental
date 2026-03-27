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
) -> str:
    """Generate a structured text briefing for AI session context.

    Scores knowledge by: confidence * 0.4 + access_frequency * 0.3 + recency * 0.3
    with type-specific decay rates:
      - MISTAKE: 30-day half-life (errors should stick around)
      - FACT: 7-day half-life
      - PATTERN: 14-day half-life
      - PREFERENCE: no decay (always relevant)
      - EPISODE: 14-day half-life

    If context_hint is provided, knowledge matching the hint gets a 0.3 score boost.
    Active lessons are always included at the top.
    """
    conn = _get_connection()
    try:
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND confidence >= 0.2 AND content NOT LIKE '[SUPERSEDED]%'"  # nosec B608
        params: list[Any] = []

        if include_types:
            placeholders = ",".join("?" for _ in include_types)
            query += f" AND knowledge_type IN ({placeholders})"
            params.extend(include_types)

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
    lines = [f"## Session Briefing ({len(entries)} items)\n"]

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
