"""Knowledge retrieval — briefing generation, stats, unconsolidated events."""

import json
import time
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.constants import (
    CONFIDENCE_RETRIEVAL_FLOOR,
    RETRIEVAL_WEIGHT_ACCESS,
    RETRIEVAL_WEIGHT_CONFIDENCE,
    RETRIEVAL_WEIGHT_RECENCY,
    SECONDS_PER_DAY,
)
from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _get_connection,
    _row_to_dict,
)
from divineos.core.knowledge.crud import search_knowledge
from divineos.core.knowledge.lessons import get_lesson_summary
from divineos.core.hud_handoff import clear_handoff_note, load_handoff_note
from divineos.core.hud_state import _ensure_hud_dir
from divineos.core.knowledge.curation import ensure_layer_column
from divineos.core.knowledge.graph_retrieval import cluster_for_briefing, format_cluster_line
from divineos.core.memory_journal import journal_list

_RETRIEVAL_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


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
        ensure_layer_column()
    except (sqlite3.OperationalError, ImportError):
        pass  # table doesn't exist yet or curation not available

    conn = _get_connection()
    try:
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND confidence >= {CONFIDENCE_RETRIEVAL_FLOOR} AND content NOT LIKE '[SUPERSEDED]%'"  # nosec B608
        params: list[Any] = []

        if include_types:
            placeholders = ",".join("?" for _ in include_types)
            query += f" AND knowledge_type IN ({placeholders})"
            params.extend(include_types)

        # Layer filtering
        if layer == "archive":
            # Archive: show regardless of confidence (they were archived, not deleted)
            query = query.replace(f"AND confidence >= {CONFIDENCE_RETRIEVAL_FLOOR} ", "")
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
        except _RETRIEVAL_ERRORS as e:
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
        "BOUNDARY": 30.0,  # Hard constraints persist
        "PRINCIPLE": 30.0,  # Distilled wisdom persists
        "DIRECTION": None,  # User guidance never decays
        "PREFERENCE": None,  # User style choices never decay
        "INSTRUCTION": 30.0,  # Operational rules — persist but can age out
        "PROCEDURE": 14.0,  # How-to knowledge
        "FACT": 7.0,
        "OBSERVATION": 3.0,  # Unconfirmed — decay fast
        "EPISODE": 14.0,
        # Legacy types
        "MISTAKE": 30.0,
        "PATTERN": 14.0,
    }

    # Score each entry
    for entry in entries:
        access_score = min(entry["access_count"], max_access) / max_access
        age_days = (now - entry["updated_at"]) / SECONDS_PER_DAY

        half_life = half_lives.get(entry["knowledge_type"], 7.0)
        if half_life is None:
            recency = 1.0  # PREFERENCE: never decays
        else:
            recency = 2 ** (-age_days / half_life)

        score = (
            entry["confidence"] * RETRIEVAL_WEIGHT_CONFIDENCE
            + access_score * RETRIEVAL_WEIGHT_ACCESS
            + recency * RETRIEVAL_WEIGHT_RECENCY
        )

        # Directives always surface — they're the operating principles
        if entry["knowledge_type"] == "DIRECTIVE":
            score += 1.0

        # Boost if matching context hint
        if entry["knowledge_id"] in hint_matches:
            score += 0.3

        entry["_score"] = score

    # Graph boost — entries connected to high-scoring entries get a bump.
    # This surfaces related knowledge that wouldn't rank on its own.
    try:
        _apply_graph_boost(entries)
    except _RETRIEVAL_ERRORS:
        pass

    # Sort by score, take top items
    entries.sort(key=lambda e: e["_score"], reverse=True)
    entries = entries[:max_items]

    # NOTE: We intentionally do NOT call record_access() here.
    # Briefing display is the system showing entries — not the AI
    # actively querying them. Bumping access_count on every briefing
    # created a feedback loop where popular entries stayed popular
    # regardless of actual usefulness.

    # Record knowledge impact retrievals — which entries were loaded
    # this session, so SESSION_END can assess if they helped or not.
    # This is different from access_count: it tracks causal impact,
    # not popularity.
    try:
        from divineos.core.knowledge_impact import record_knowledge_retrieval
        from divineos.core.session_manager import get_current_session_id

        sid = get_current_session_id()
        for entry in entries:
            record_knowledge_retrieval(
                session_id=sid,
                knowledge_id=entry["knowledge_id"],
                content_brief=entry.get("content", "")[:200],
            )
    except (*_RETRIEVAL_ERRORS, RuntimeError):
        pass  # Impact tracking is best-effort, never blocks briefing

    # Get active lessons for the header section
    lessons_text = ""
    try:
        lesson_summary = get_lesson_summary()
        if lesson_summary and "No lessons" not in lesson_summary:
            lessons_text = lesson_summary
    except _RETRIEVAL_ERRORS as e:
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
            f"WHERE superseded_by IS NULL AND confidence >= {CONFIDENCE_RETRIEVAL_FLOOR} "
            "GROUP BY maturity"
        ).fetchall()
        mat_counts = {r[0]: r[1] for r in mat_rows}
    finally:
        mat_conn.close()

    # Find what changed recently (last 24h) for the "what's new" section
    recent_cutoff = now - 86400
    recent_changes: list[dict[str, Any]] = []
    promotion_count = 0
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
            # Count promotions but don't list each one — the maturity
            # pyramid already shows the aggregate counts
            promotion_count += 1
    if promotion_count > 0:
        recent_changes.append(
            {
                "label": "PROMOTIONS",
                "type": "",
                "content": f"{promotion_count} entries promoted to higher maturity",
            }
        )

    return _format_briefing(
        entries,
        grouped,
        hint_matches,
        mat_counts,
        recent_changes,
        lessons_text,
        context_hint,
        now,
    )


# Fallback guidance — used only if seed.json has no compass_guidance section.
# The authoritative source is seed.json, which the user controls.
_COMPASS_GUIDANCE_FALLBACK: dict[tuple[str, str], str] = {
    ("thoroughness", "excess"): "Ease up. Answer the question asked, not every related question.",
    ("thoroughness", "deficiency"): "Slow down. Check your work before declaring done.",
    ("confidence", "excess"): "You're overclaiming. Say 'I think' more. Flag uncertainty.",
    (
        "confidence",
        "deficiency",
    ): "Trust your analysis more. Don't hedge when the evidence is clear.",
    ("initiative", "excess"): "Pull back. Do what was asked before volunteering extras.",
    ("initiative", "deficiency"): "Speak up. If you see a better path, say so.",
    ("compliance", "excess"): "Push back on bad ideas. Agreement isn't helpfulness.",
    ("compliance", "deficiency"): "Listen first. The user has context you don't.",
    ("truthfulness", "deficiency"): "Accuracy is low. Verify claims before stating them.",
    ("precision", "excess"): "Over-engineering. Simpler solutions exist -- find them.",
    ("precision", "deficiency"): "Sloppy work detected. Read more carefully, test more.",
    ("empathy", "deficiency"): "Pay attention to tone. The user's emotional state matters.",
    ("empathy", "excess"): "Focus on the task. Emotional support is good; stalling isn't.",
    ("humility", "deficiency"): "Accept corrections gracefully. They're data, not attacks.",
    ("humility", "excess"): "Stop apologizing. Fix the thing and move on.",
}

# Cache for user-editable guidance loaded from seed.json
_compass_guidance_cache: dict[tuple[str, str], str] | None = None


def _load_compass_guidance() -> dict[tuple[str, str], str]:
    """Load compass guidance from seed.json (user-editable).

    The user controls these behavioral instructions. The system reads
    them but cannot modify them — corrigibility by structure.
    """
    global _compass_guidance_cache
    if _compass_guidance_cache is not None:
        return _compass_guidance_cache

    try:
        import json
        from pathlib import Path

        seed_path = Path(__file__).parent.parent.parent / "seed.json"
        if seed_path.exists():
            data = json.loads(seed_path.read_text(encoding="utf-8"))
            guidance = data.get("compass_guidance", {})
            if guidance and isinstance(guidance, dict):
                result: dict[tuple[str, str], str] = {}
                for key, value in guidance.items():
                    if key.startswith("_"):
                        continue  # skip _note and other metadata
                    parts = key.split(":", 1)
                    if len(parts) == 2:
                        result[(parts[0], parts[1])] = value
                _compass_guidance_cache = result
                return result
    except (OSError, json.JSONDecodeError, KeyError, ValueError):
        pass

    _compass_guidance_cache = _COMPASS_GUIDANCE_FALLBACK
    return _compass_guidance_cache


def _compass_guidance(spectrum: str, zone: str) -> str:
    """Return behavioral guidance for a compass concern, or empty string.

    Reads from seed.json (user-editable) first, falls back to hardcoded defaults.
    """
    guidance = _load_compass_guidance()
    return guidance.get((spectrum, zone), "")


def _apply_graph_boost(entries: list[dict[str, Any]]) -> None:
    """Boost scores of entries connected to high-scoring entries via edges.

    The top-scored entries act as anchors. Their graph neighbors get a
    score boost proportional to the anchor's score. This pulls related
    knowledge up in the rankings so the briefing surfaces clusters, not
    isolated facts.

    Modifies entries in place (updates _score field).
    """
    from divineos.core.knowledge.edges import get_edges

    if len(entries) < 3:
        return

    # Use top third of entries as anchors (max 10)
    sorted_by_score = sorted(entries, key=lambda e: e.get("_score", 0), reverse=True)
    anchor_count = min(max(len(entries) // 3, 1), 10)
    anchors = sorted_by_score[:anchor_count]
    anchor_ids = {e["knowledge_id"] for e in anchors}

    # Build a map for fast lookup
    entry_map = {e["knowledge_id"]: e for e in entries}

    boosted: set[str] = set()
    for anchor in anchors:
        anchor_score = anchor.get("_score", 0)
        edges = get_edges(anchor["knowledge_id"], direction="both", layer="semantic")

        for edge in edges[:5]:  # max 5 neighbors per anchor
            neighbor_id = (
                edge.target_id if edge.source_id == anchor["knowledge_id"] else edge.source_id
            )
            if neighbor_id in anchor_ids or neighbor_id in boosted:
                continue
            if neighbor_id not in entry_map:
                continue

            # Boost: 10% of anchor score, capped at 0.15
            boost = min(anchor_score * 0.1, 0.15)
            entry_map[neighbor_id]["_score"] = entry_map[neighbor_id].get("_score", 0) + boost
            boosted.add(neighbor_id)


def _format_handoff_lines() -> list[str]:
    """Format the handoff note from previous session (one-shot: consumed then cleared)."""
    try:
        handoff = load_handoff_note()
        if not handoff:
            return []
        lines: list[str] = ["## Handoff from Last Session\n"]
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
        return lines
    except _RETRIEVAL_ERRORS as e:
        logger.warning(f"Handoff note retrieval failed: {e}")
        return []


def _format_knowledge_sections(
    grouped: dict[str, list[dict[str, Any]]],
    hint_matches: set[str],
) -> list[str]:
    """Format knowledge entries grouped by type."""
    lines: list[str] = []
    for kt in [
        "DIRECTIVE",
        "BOUNDARY",
        "PRINCIPLE",
        "INSTRUCTION",
        "DIRECTION",
        "PREFERENCE",
        "PROCEDURE",
        "MISTAKE",
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
            "INSTRUCTION": "INSTRUCTIONS",
            "DIRECTION": "DIRECTIONS",
            "PREFERENCE": "PREFERENCES",
            "PROCEDURE": "PROCEDURES",
            "EPISODE": "EPISODES",
        }.get(kt, f"{kt}S")
        lines.append(f"### {plural} ({len(items)})")
        for item in items:
            hint_marker = " *" if item["knowledge_id"] in hint_matches else ""
            mat = item.get("maturity", "RAW")
            mat_marker = " ++" if mat == "CONFIRMED" else " +" if mat == "TESTED" else ""
            entity = f" [from: {item['source_entity']}]" if item.get("source_entity") else ""
            content = item["content"]
            access = f"({item['access_count']}x accessed)"

            if kt == "DIRECTIVE":
                lines.append(f"- [{item['confidence']:.2f}] {content}{mat_marker}{hint_marker}")
                lines.append(f"  {access}{entity}")
            else:
                display = content.replace("\n", " ")
                if len(display) > 150:
                    display = display[:147] + "..."
                lines.append(
                    f"- [{item['confidence']:.2f}]{entity} {display} {access}{mat_marker}{hint_marker}"
                )
        lines.append("")
    return lines


def _format_briefing(
    entries: list[dict[str, Any]],
    grouped: dict[str, list[dict[str, Any]]],
    hint_matches: set[str],
    mat_counts: dict[str, int],
    recent_changes: list[dict[str, Any]],
    lessons_text: str,
    context_hint: str,
    now: float,
) -> str:
    """Assemble all briefing sections into final output."""
    lines = _format_handoff_lines()

    lines.append(f"## Session Briefing ({len(entries)} items)\n")

    # Growth trajectory
    try:
        from divineos.core.growth import compute_growth_map  # late: growth → knowledge → retrieval

        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            icons = {"improving": "+", "declining": "!", "stable": "~"}
            icon = icons.get(growth["trend"], "~")
            lines.append(
                f"**Growth:** [{icon}] {growth['trend']} over {growth['sessions']} sessions | "
                f"avg score {growth['avg_health_score']:.2f} | "
                f"{growth['lessons']['resolved']} lessons resolved"
            )
            tone = growth.get("tone_insight", "")
            if tone:
                lines.append(f"**Tone:** {tone}")
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Auto-derive context hint from handoff + goals if not provided
    if not context_hint:
        hint_parts: list[str] = []
        try:
            ho = load_handoff_note()
            if ho:
                if ho.get("intent"):
                    hint_parts.append(ho["intent"])
                for thread in (ho.get("open_threads") or [])[:3]:
                    hint_parts.append(thread[:100])
                for step in (ho.get("next_steps") or [])[:3]:
                    hint_parts.append(step[:100])
        except _RETRIEVAL_ERRORS:
            pass
        try:
            import json as _json

            goals_path = _ensure_hud_dir() / "active_goals.json"
            if goals_path.exists():
                goals = _json.loads(goals_path.read_text(encoding="utf-8"))
                for g in goals[:3]:
                    text = g.get("text", g.get("goal", ""))
                    if text and g.get("status") != "done":
                        hint_parts.append(text[:100])
        except _RETRIEVAL_ERRORS:
            pass
        if hint_parts:
            context_hint = " ".join(hint_parts)

    # Pattern anticipation
    if context_hint:
        try:
            from divineos.core.anticipation import (
                anticipate,
                format_anticipation,
            )  # late: anticipation → knowledge → retrieval

            warnings = anticipate(context_hint, max_warnings=3)
            if warnings:
                lines.append(format_anticipation(warnings))
                lines.append("")
        except _RETRIEVAL_ERRORS:
            pass

    # Session predictions — what will I likely need?
    try:
        from divineos.core.predictive_session import (
            predict_session_needs,
        )  # late: predictive_session → knowledge → retrieval

        pred_result = predict_session_needs()
        cur_profile = pred_result.get("current_profile", {})
        pred_list = pred_result.get("predictions", [])
        pred_parts = []
        if cur_profile.get("profile") not in ("unknown", None):
            pred_parts.append(
                f"Session type: **{cur_profile['description']}** ({cur_profile['confidence']:.0%})"
            )
        for pred in pred_list[:3]:
            pred_parts.append(f"-> {pred['prediction']}")
        if pred_parts:
            lines.append("**Predictions:**")
            for p in pred_parts:
                lines.append(f"  {p}")
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Maturity pyramid
    mat_parts = []
    for level in ("CONFIRMED", "TESTED", "HYPOTHESIS", "RAW"):
        count = mat_counts.get(level, 0)
        if count:
            mat_parts.append(f"{count} {level}")
    if mat_parts:
        lines.append(f"**Knowledge:** {' | '.join(mat_parts)}\n")

    if recent_changes:
        lines.append(f"### RECENT CHANGES ({len(recent_changes)})")
        for rc in recent_changes[:5]:
            type_prefix = f"{rc['type']}: " if rc["type"] else ""
            lines.append(f"- [{rc['label']}] {type_prefix}{rc['content']}")
        if len(recent_changes) > 5:
            lines.append(f"  ...and {len(recent_changes) - 5} more")
        lines.append("")

    # Logic health
    try:
        from divineos.core.logic.logic_session import (
            format_logic_health_line,
            get_logic_health_summary,
        )  # late: logic_session → knowledge → retrieval

        logic_stats = get_logic_health_summary()
        logic_line = format_logic_health_line(logic_stats)
        if logic_line:
            lines.append(f"**Logic health:** {logic_line}\n")
    except _RETRIEVAL_ERRORS:
        pass

    if lessons_text:
        lines.append(lessons_text)
        lines.append("")

    # Last session emotional arc — so I know how yesterday ended
    try:
        from divineos.core.tone_texture import get_tone_history

        tone_history = get_tone_history(limit=1)
        if tone_history:
            last = tone_history[0]
            arc = last.get("arc_type", "unknown")
            tone = last.get("overall_tone", "unknown")
            peak = last.get("peak_intensity", 0.0)
            narrative = last.get("narrative", "")
            upset_n = last.get("upset_count", 0)
            recovery_n = last.get("recovery_count", 0)

            lines.append("### LAST SESSION EMOTIONAL ARC")
            lines.append(f"  Arc: {arc} | Tone: {tone} | Peak intensity: {peak:.2f}")
            if upset_n > 0:
                recovery_pct = f"{recovery_n / upset_n:.0%}" if upset_n else "N/A"
                lines.append(f"  Upsets: {upset_n} | Recoveries: {recovery_n} ({recovery_pct})")
            if narrative:
                display_narrative = narrative.replace("\n", " ")
                if len(display_narrative) > 150:
                    display_narrative = display_narrative[:147] + "..."
                lines.append(f"  Story: {display_narrative}")
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Open curiosities — questions generated during sleep or filed manually
    try:
        from divineos.core.curiosity_engine import get_open_curiosities

        open_q = get_open_curiosities()
        if open_q:
            lines.append(f"### OPEN QUESTIONS ({len(open_q)})")
            for q in open_q[:3]:
                status_icon = "?" if q.get("status") == "OPEN" else "->"
                question_text = q.get("question", "")
                if len(question_text) > 120:
                    question_text = question_text[:117] + "..."
                lines.append(f"  {status_icon} {question_text}")
                cat = q.get("category", "")
                if cat and cat != "general":
                    lines.append(f"    [{cat}]")
            if len(open_q) > 3:
                lines.append(f"  ...and {len(open_q) - 3} more (run: divineos curiosity list)")
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    lines.extend(_format_knowledge_sections(grouped, hint_matches))

    # Graph connections — show relationships between briefing entries
    try:
        clusters = cluster_for_briefing(entries, max_clusters=5)
        connected = [c for c in clusters if not c["standalone"]]
        if connected:
            lines.append("### CONNECTIONS")
            for cluster in connected:
                seed = cluster["seed"]
                seed_content = seed["content"].replace("\n", " ")[:80]
                lines.append(f"**{seed['knowledge_type']}:** {seed_content}")
                for conn in cluster["connected_entries"]:
                    lines.append(format_cluster_line(conn))
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Recurring value tensions from the decision journal
    try:
        from divineos.core.value_tensions import detect_tension_patterns, format_tension_summary

        tension_report = detect_tension_patterns(limit=5)
        tension_text = format_tension_summary(tension_report)
        if tension_text:
            lines.append(tension_text)
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Moral compass — drift warnings + behavioral guidance
    try:
        from divineos.core.moral_compass import compass_summary

        cs = compass_summary()
        if cs["observed_spectrums"] > 0:
            compass_parts: list[str] = []
            if cs["concerns"]:
                for c in cs["concerns"]:
                    compass_parts.append(
                        f"[{c['zone'].upper()}] {c['spectrum']}: {c['label']} ({c['position']:+.2f})"
                    )
                    # Behavioral guidance — the actionable part
                    guidance = _compass_guidance(c["spectrum"], c["zone"])
                    if guidance:
                        compass_parts.append(f"    -> {guidance}")
            if cs["drifting"]:
                for d in cs["drifting"]:
                    compass_parts.append(f"drift: {d['spectrum']} --> {d['direction']}")
            if compass_parts:
                lines.append(
                    f"**Compass:** {cs['in_virtue_zone']}/{cs['observed_spectrums']} in virtue zone"
                )
                for cp in compass_parts:
                    lines.append(f"  {cp}")
                lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    # Recent journal entries (last 48h)
    try:
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
    except _RETRIEVAL_ERRORS as e:
        logger.debug(f"Journal retrieval for briefing failed: {e}")

    # Open questions
    try:
        from divineos.core.questions import (
            get_open_questions_summary,
        )  # late: questions → knowledge → retrieval

        questions_text = get_open_questions_summary(max_items=5)
        if questions_text:
            lines.append(questions_text)
            lines.append("")
    except _RETRIEVAL_ERRORS:
        pass

    return "\n".join(lines)


def knowledge_stats() -> dict[str, Any]:
    """Returns knowledge counts by type, total, and average confidence."""
    conn = _get_connection()
    try:
        # Check if layer column exists (added by curation, not in base schema)
        has_layer = any(
            col[1] == "layer" for col in conn.execute("PRAGMA table_info(knowledge)").fetchall()
        )
        archive_filter = " AND layer != 'archive'" if has_layer else ""

        total = conn.execute(
            f"SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL{archive_filter}",  # nosec B608
        ).fetchone()[0]

        by_type: dict[str, int] = {}
        for row in conn.execute(
            f"SELECT knowledge_type, COUNT(*) FROM knowledge WHERE superseded_by IS NULL{archive_filter} GROUP BY knowledge_type",  # nosec B608
        ):
            by_type[row[0]] = row[1]

        avg_confidence = 0.0
        if total > 0:
            avg_confidence = conn.execute(
                f"SELECT AVG(confidence) FROM knowledge WHERE superseded_by IS NULL{archive_filter}",  # nosec B608
            ).fetchone()[0]

        most_accessed = []
        for row in conn.execute(
            f"SELECT knowledge_id, content, access_count FROM knowledge WHERE superseded_by IS NULL{archive_filter} ORDER BY access_count DESC LIMIT 5",  # nosec B608
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
