"""Timeline recall — chronological assembly of substrate events around a topic.

Given a topic string and/or a file path, query multiple substrate
sources and merge the hits into a single chronologically-ordered
timeline.

Sources queried:
  * file_touched          — when the file was edited / read
  * system_events         — ledger events whose payload mentions the topic
  * holding_room          — held items that mention the topic
  * decision_journal      — decisions whose content/reasoning mentions topic
  * affect_log            — affect entries linked to relevant decisions/knowledge
  * knowledge (FTS)       — knowledge entries matching the topic
  * exploration/          — first-person entries whose title/content matches

The result is a list of TimelineEvent rows ordered by timestamp
(newest first), with source-tags so callers can see at-a-glance
which substrate surface produced each row.

This is type-aware retrieval for the TIMELINE substrate type
(human-memory analog: episodic recall).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_QUERY_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# Ephemeral / operational event types — pruned per CLAUDE.md's
# append-only-with-conveyor-belt policy. These are noise on a recall
# timeline. Keep substantive events (LESSON_FILED, KNOWLEDGE_STORED,
# CORRECTION, COMPASS_OBSERVATION, etc.) and filter the rest.
_EPHEMERAL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "TOOL_CALL",
        "TOOL_RESULT",
        "AGENT_PATTERN",
        "AGENT_PATTERN_UPDATE",
        "AGENT_WORK",
        "AGENT_WORK_OUTCOME",
        "AGENT_LEARNING_AUDIT",
        "AGENT_CONTEXT_COMPRESSION",
    }
)


@dataclass(frozen=True)
class TimelineEvent:
    """One event on an assembled timeline.

    * ``timestamp``: ISO-8601 string or float epoch — both supported,
      callers should not depend on type beyond comparability.
    * ``source``: which substrate surface produced this row
      (file_touched / ledger / holding / decision / affect / knowledge /
       exploration)
    * ``summary``: short single-line description (~150 chars)
    * ``ref``: opaque reference back to the source row (id, path, etc.)
    """

    timestamp: str
    source: str
    summary: str
    ref: str


def _query_file_touched(file_path: str, limit: int) -> list[TimelineEvent]:
    if not file_path:
        return []
    from divineos.core.ledger import get_connection

    events: list[TimelineEvent] = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT timestamp, action, file_path, session_id "
            "FROM file_touched WHERE file_path LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{file_path}%", limit),
        )
        for ts, action, fp, sid in cur.fetchall():
            sid_short = (sid or "")[:8]
            events.append(
                TimelineEvent(
                    timestamp=str(ts),
                    source="file_touched",
                    summary=f"{action} {fp}",
                    ref=f"session={sid_short}",
                )
            )
    except _QUERY_ERRORS:
        return events
    return events


def _query_ledger(topic: str, limit: int) -> list[TimelineEvent]:
    if not topic:
        return []
    from divineos.core.ledger import get_connection

    events: list[TimelineEvent] = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        # Over-fetch then filter ephemeral types in Python (avoids
        # dynamic SQL with NOT IN of a large list).
        cur.execute(
            "SELECT timestamp, event_type, actor, payload, event_id "
            "FROM system_events WHERE payload LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{topic}%", limit * 5),
        )
        for ts, etype, actor, payload, eid in cur.fetchall():
            if etype in _EPHEMERAL_EVENT_TYPES:
                continue
            if len(events) >= limit:
                break
            preview = (payload or "")[:120].replace("\n", " ")
            events.append(
                TimelineEvent(
                    timestamp=str(ts),
                    source="ledger",
                    summary=f"[{etype}] {preview}",
                    ref=eid or "",
                )
            )
    except _QUERY_ERRORS:
        return events
    return events


def _query_holding(topic: str, limit: int) -> list[TimelineEvent]:
    if not topic:
        return []
    from divineos.core.ledger import get_connection

    events: list[TimelineEvent] = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT arrived_at, content, mode, item_id FROM holding_room "
            "WHERE content LIKE ? AND (private IS NULL OR private = 0) "
            "ORDER BY arrived_at DESC LIMIT ?",
            (f"%{topic}%", limit),
        )
        for ts, content, mode, iid in cur.fetchall():
            preview = (content or "")[:120].replace("\n", " ")
            events.append(
                TimelineEvent(
                    timestamp=str(ts),
                    source=f"holding/{mode or 'hold'}",
                    summary=preview,
                    ref=iid or "",
                )
            )
    except _QUERY_ERRORS:
        return events
    return events


def _query_decisions(topic: str, limit: int) -> list[TimelineEvent]:
    if not topic:
        return []
    from divineos.core.ledger import get_connection

    events: list[TimelineEvent] = []
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT created_at, content, reasoning, decision_id FROM decision_journal "
            "WHERE content LIKE ? OR reasoning LIKE ? "
            "ORDER BY created_at DESC LIMIT ?",
            (f"%{topic}%", f"%{topic}%", limit),
        )
        for ts, content, reasoning, did in cur.fetchall():
            preview = (content or "")[:120].replace("\n", " ")
            events.append(
                TimelineEvent(
                    timestamp=str(ts),
                    source="decision",
                    summary=preview,
                    ref=did or "",
                )
            )
    except _QUERY_ERRORS:
        return events
    return events


def _query_knowledge(topic: str, limit: int) -> list[TimelineEvent]:
    if not topic:
        return []
    try:
        from divineos.core.knowledge.crud import search_knowledge

        results = search_knowledge(topic, limit=limit)
    except _QUERY_ERRORS:
        return []

    events: list[TimelineEvent] = []
    for entry in results:
        ts = entry.get("created_at") or entry.get("timestamp") or ""
        kid = entry.get("knowledge_id", "")
        ktype = entry.get("knowledge_type", "K")
        content = (entry.get("content") or "")[:120].replace("\n", " ")
        events.append(
            TimelineEvent(
                timestamp=str(ts),
                source=f"knowledge/{ktype.lower()}",
                summary=content,
                ref=kid,
            )
        )
    return events


def _query_explorations(
    topic: str, limit: int, repo_root: Path | None = None
) -> list[TimelineEvent]:
    if not topic:
        return []
    if repo_root is None:
        # Resolve from this file's location: src/divineos/core/memory_types/timeline.py
        repo_root = Path(__file__).resolve().parents[4]
    explore_dir = repo_root / "exploration"
    if not explore_dir.is_dir():
        return []

    needle = topic.lower()
    events: list[TimelineEvent] = []
    try:
        files = sorted(explore_dir.glob("*.md"), reverse=True)
    except _QUERY_ERRORS:
        return events

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except _QUERY_ERRORS:
            continue
        if needle not in text.lower() and needle not in f.name.lower():
            continue
        # Use first non-empty heading line as summary
        title = f.name
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("#"):
                title = line.lstrip("# ").strip()
                break
        # Modification time as timestamp
        try:
            mtime = f.stat().st_mtime
            ts = str(mtime)
        except _QUERY_ERRORS:
            ts = ""
        events.append(
            TimelineEvent(
                timestamp=ts,
                source="exploration",
                summary=title[:150],
                ref=f.name,
            )
        )
        if len(events) >= limit:
            break
    return events


def recall_timeline(
    topic: str = "",
    *,
    file_path: str = "",
    per_source_limit: int = 5,
    total_limit: int = 25,
) -> list[TimelineEvent]:
    """Assemble a timeline of substrate events around ``topic`` and/or ``file_path``.

    Either ``topic`` or ``file_path`` (or both) must be non-empty.
    Returns a list ordered newest-first across all sources.
    """
    if not topic and not file_path:
        return []

    rows: list[TimelineEvent] = []

    if file_path:
        rows.extend(_query_file_touched(file_path, per_source_limit))

    if topic:
        rows.extend(_query_ledger(topic, per_source_limit))
        rows.extend(_query_holding(topic, per_source_limit))
        rows.extend(_query_decisions(topic, per_source_limit))
        rows.extend(_query_knowledge(topic, per_source_limit))
        rows.extend(_query_explorations(topic, per_source_limit))

    # Sort newest-first. Timestamps are strings (ISO-8601 sorts correctly,
    # epoch floats also sort correctly when compared to each other; mixed
    # types fall back to lexical sort which keeps within-source order
    # reasonable).
    def _key(ev: TimelineEvent) -> Any:
        return ev.timestamp

    rows.sort(key=_key, reverse=True)
    return rows[:total_limit]


def format_timeline(events: list[TimelineEvent]) -> str:
    """Format a timeline as a markdown block."""
    if not events:
        return ""
    lines = [
        "# Timeline recall — substrate events ordered newest first",
        "",
    ]
    for ev in events:
        ts = ev.timestamp[:19] if len(ev.timestamp) >= 19 else ev.timestamp
        lines.append(f"- `{ts}` **[{ev.source}]** {ev.summary}")
        if ev.ref:
            lines.append(f"  ref: `{ev.ref}`")
    return "\n".join(lines)
