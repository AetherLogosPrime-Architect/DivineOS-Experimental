"""Decision superposition implementation.

Storage shape: superpositions are AGENT_PATTERN events with
``kind = "superposition_open"`` or ``"superposition_collapse"``. The
active set is reconstructed by finding open events not yet matched
by a collapse event. Append-only; no in-place mutation.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

_DS_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)


@dataclass(frozen=True)
class Superposition:
    """A deliberately-held set of candidate decisions.

    Attributes:
        superposition_id: Unique id.
        question: The decision being held open ("which test mechanism to use?").
        options: The candidate options being held equipotent.
        resolve_trigger: What event/data would collapse this (e.g.
            "Aletheia's audit on this lands" or "CI run completes").
        opened_at: Timestamp of when the superposition was opened.
        opened_event_id: Ledger event_id of the opening record.
    """

    superposition_id: str
    question: str
    options: tuple[str, ...]
    resolve_trigger: str
    opened_at: float
    opened_event_id: str


def open_superposition(question: str, options: list[str], resolve_trigger: str) -> str:
    """Record a deliberately-held superposition.

    Returns the superposition_id (or empty string on failure). At
    least two options must be provided — a single option isn't a
    superposition, it's a decision.
    """
    if len([o for o in options if (o or "").strip()]) < 2:
        return ""
    if not (question or "").strip():
        return ""

    sid = f"super-{uuid.uuid4().hex[:12]}"
    payload: dict[str, Any] = {
        "kind": "superposition_open",
        "superposition_id": sid,
        "question": question.strip(),
        "options": [o.strip() for o in options if o.strip()],
        "resolve_trigger": (resolve_trigger or "").strip(),
        "ts": time.time(),
    }
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="AGENT_PATTERN",
            actor="aether",
            payload=payload,
        )
    except _DS_ERRORS:
        return ""
    return sid


def collapse(superposition_id: str, chosen_option: str, reason: str) -> str:
    """Resolve a held superposition into a concrete decision.

    Records the collapse event (the "which option" + "why now") and
    also files a regular decision-journal entry so the collapsed
    decision joins the normal decision-history.

    Returns the decision_id (or empty string on failure).
    """
    if not (superposition_id or "").strip():
        return ""
    if not (chosen_option or "").strip():
        return ""

    # Record the collapse on the ledger.
    collapse_payload: dict[str, Any] = {
        "kind": "superposition_collapse",
        "superposition_id": superposition_id,
        "chosen_option": chosen_option.strip(),
        "reason": (reason or "").strip(),
        "ts": time.time(),
    }
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="AGENT_PATTERN",
            actor="aether",
            payload=collapse_payload,
        )
    except _DS_ERRORS:
        return ""

    # File the actual decision via the decision journal.
    try:
        from divineos.core.decision_journal import record_decision

        decision_id = record_decision(
            content=chosen_option.strip(),
            reasoning=(
                f"Collapsed from superposition {superposition_id}. Reason: {(reason or '').strip()}"
            ),
        )
        return str(decision_id or "")
    except _DS_ERRORS:
        return ""


def _load_superposition_events() -> tuple[list[dict], list[dict]]:
    """Return (open_events, collapse_events) for reconstruction."""
    try:
        from divineos.core.ledger import search_events
    except _DS_ERRORS:
        return [], []

    opens = []
    collapses = []
    try:
        events = search_events(keyword="superposition_", limit=500) or []
    except _DS_ERRORS:
        return [], []

    for ev in events:
        if ev.get("event_type") != "AGENT_PATTERN":
            continue
        raw = ev.get("payload") or ev.get("content")
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except _DS_ERRORS:
            continue
        if not isinstance(payload, dict):
            continue
        kind = payload.get("kind")
        if kind == "superposition_open":
            opens.append({"payload": payload, "event_id": ev.get("event_id") or ev.get("id") or ""})
        elif kind == "superposition_collapse":
            collapses.append(
                {"payload": payload, "event_id": ev.get("event_id") or ev.get("id") or ""}
            )

    return opens, collapses


def active_superpositions() -> list[Superposition]:
    """Return all open superpositions that haven't been collapsed yet,
    most-recent first."""
    opens, collapses = _load_superposition_events()
    collapsed_ids = {str(c["payload"].get("superposition_id") or "") for c in collapses}

    out: list[Superposition] = []
    for o in opens:
        p = o["payload"]
        sid = str(p.get("superposition_id") or "")
        if not sid or sid in collapsed_ids:
            continue
        opts = p.get("options") or []
        out.append(
            Superposition(
                superposition_id=sid,
                question=str(p.get("question") or ""),
                options=tuple(str(x) for x in opts),
                resolve_trigger=str(p.get("resolve_trigger") or ""),
                opened_at=float(p.get("ts") or 0.0),
                opened_event_id=str(o["event_id"]),
            )
        )
    out.sort(key=lambda s: s.opened_at, reverse=True)
    return out


__all__ = [
    "Superposition",
    "active_superpositions",
    "collapse",
    "open_superposition",
]
