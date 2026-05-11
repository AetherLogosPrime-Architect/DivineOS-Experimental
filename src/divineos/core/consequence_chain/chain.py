"""Decision → outcome → lesson chain joining.

Heuristic v1: same-session + time-window proximity. The join is a
queryable surface over data that already exists; future refinements
can tighten the heuristic without changing the public API.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

_CC_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)

# Time window (seconds) within which an outcome or lesson is considered
# downstream of a decision. 24h is loose but keeps the v1 join generous.
_CHAIN_WINDOW_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class ConsequenceChain:
    """A decision and the outcomes/lessons that followed.

    Attributes:
        decision_id: The originating decision id.
        decision_summary: Short text describing the decision.
        session_id: The session in which the decision was filed.
        outcome_event_ids: Ledger event ids classified as outcomes
            within the chain window.
        lesson_ids: Knowledge-store entries (lessons) filed within
            the chain window in the same session.
        decision_ts: Timestamp of the originating decision.
    """

    decision_id: str
    decision_summary: str
    session_id: str
    outcome_event_ids: tuple[str, ...] = field(default_factory=tuple)
    lesson_ids: tuple[str, ...] = field(default_factory=tuple)
    decision_ts: float = 0.0


def _fetch_decision(decision_id: str) -> dict | None:
    try:
        from divineos.core.decision_journal import get_decision

        result = get_decision(decision_id)
        return dict(result) if result is not None else None
    except _CC_ERRORS:
        return None


def _recent_decisions(limit: int = 50) -> list[dict]:
    try:
        from divineos.core.decision_journal import list_decisions

        rows = list_decisions(limit=limit) or []
        return [dict(r) for r in rows]
    except _CC_ERRORS:
        return []


def _lessons_in_window(session_id: str, after_ts: float, before_ts: float) -> list[tuple[str, str]]:
    """Return (knowledge_id, content) for lessons in the time window
    and (where possible) tied to the session."""
    try:
        from divineos.core.knowledge import get_connection

        conn = get_connection()
    except _CC_ERRORS:
        return []

    try:
        # Knowledge entries have created_at and (sometimes) session_id.
        # The conservative join: time-window first, then prefer same-session.
        rows = conn.execute(
            """
            SELECT id, content
            FROM knowledge
            WHERE created_at >= ? AND created_at <= ?
            ORDER BY created_at ASC
            LIMIT 200
            """,
            (after_ts, before_ts),
        ).fetchall()
    except _CC_ERRORS:
        return []
    finally:
        try:
            conn.close()
        except _CC_ERRORS:
            pass

    return [(str(r[0]), str(r[1] or "")) for r in rows]


def _outcome_events_in_window(session_id: str, after_ts: float, before_ts: float) -> list[str]:
    """Return ledger event_ids classified as outcomes within the window.
    Uses the ledger's public ``get_events`` surface rather than direct
    SQL so this stays decoupled from the ledger's storage schema."""
    try:
        from divineos.core.ledger import get_events

        outcome_types = [
            "OUTCOME",
            "OUTCOME_MEASURED",
            "LESSON_LEARNED",
            "CORRECTION_APPLIED",
            "COMPLETION_BOUNDARY",
        ]
        out_ids: list[str] = []
        for et in outcome_types:
            try:
                events = get_events(event_type=et, limit=200) or []
            except _CC_ERRORS:
                continue
            for ev in events:
                ts = float(ev.get("timestamp") or ev.get("ts") or 0.0)
                if after_ts <= ts <= before_ts:
                    eid = str(ev.get("event_id") or ev.get("id") or "")
                    if eid:
                        out_ids.append(eid)
        return out_ids
    except _CC_ERRORS:
        return []


def chain_from_decision(decision_id: str) -> ConsequenceChain | None:
    """Build the consequence chain forward from a decision.

    Returns None if the decision isn't found. Otherwise returns a
    ConsequenceChain with outcomes and lessons that fall in the
    time window after the decision.
    """
    decision = _fetch_decision(decision_id)
    if decision is None:
        return None

    decision_ts = float(decision.get("ts") or decision.get("created_at") or 0.0)
    session_id = str(decision.get("session_id") or "")
    summary = str(decision.get("what") or decision.get("decision") or "")[:200]

    if decision_ts <= 0:
        # Without a timestamp we can't compute a window; return empty chain.
        return ConsequenceChain(
            decision_id=decision_id,
            decision_summary=summary,
            session_id=session_id,
            decision_ts=0.0,
        )

    after_ts = decision_ts
    before_ts = decision_ts + _CHAIN_WINDOW_SECONDS

    outcomes = tuple(_outcome_events_in_window(session_id, after_ts, before_ts))
    lessons = tuple(kid for kid, _content in _lessons_in_window(session_id, after_ts, before_ts))

    return ConsequenceChain(
        decision_id=decision_id,
        decision_summary=summary,
        session_id=session_id,
        outcome_event_ids=outcomes,
        lesson_ids=lessons,
        decision_ts=decision_ts,
    )


def chain_to_lesson(lesson_id: str) -> list[ConsequenceChain]:
    """Trace backward from a lesson to the decision(s) that likely
    produced it. Returns chains for any decisions within the chain
    window before the lesson was filed.

    Returns an empty list if the lesson isn't found or no candidates
    exist in the window.
    """
    try:
        from divineos.core.knowledge import get_connection

        conn = get_connection()
        row = conn.execute(
            "SELECT created_at FROM knowledge WHERE id = ? LIMIT 1",
            (lesson_id,),
        ).fetchone()
        conn.close()
    except _CC_ERRORS:
        return []

    if not row:
        return []
    lesson_ts = float(row[0] or 0.0)
    if lesson_ts <= 0:
        return []

    window_start = lesson_ts - _CHAIN_WINDOW_SECONDS
    candidates = [
        d
        for d in _recent_decisions(limit=200)
        if window_start <= float(d.get("ts") or d.get("created_at") or 0.0) <= lesson_ts
    ]
    chains: list[ConsequenceChain] = []
    for d in candidates:
        did = str(d.get("decision_id") or d.get("id") or "")
        if not did:
            continue
        ch = chain_from_decision(did)
        if ch is not None and lesson_id in ch.lesson_ids:
            chains.append(ch)
    return chains


def recent_chains(limit: int = 10) -> list[ConsequenceChain]:
    """Return chains for the most recent decisions that have at least
    one downstream outcome or lesson."""
    chains: list[ConsequenceChain] = []
    for d in _recent_decisions(limit=limit * 3):
        did = str(d.get("decision_id") or d.get("id") or "")
        if not did:
            continue
        ch = chain_from_decision(did)
        if ch is None:
            continue
        if ch.outcome_event_ids or ch.lesson_ids:
            chains.append(ch)
        if len(chains) >= limit:
            break
    return chains


__all__ = [
    "ConsequenceChain",
    "chain_from_decision",
    "chain_to_lesson",
    "recent_chains",
]
