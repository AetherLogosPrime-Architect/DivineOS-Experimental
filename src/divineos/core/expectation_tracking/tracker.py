"""Expectation tracker implementation.

Storage shape: each prediction is an AGENT_PATTERN event with
``kind = "expectation_open"``; closing the loop is an
``"expectation_close"`` event referencing the same expectation_id.
Append-only; no in-place mutation. The open set is reconstructed
by finding opens not matched by closes.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass

_ET_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)


@dataclass(frozen=True)
class Expectation:
    """A prediction and (if closed) its actual.

    Attributes:
        expectation_id: Unique id.
        claim: The predicted outcome ("Aletheia's audit will CONFIRMS this").
        basis: The evidence supporting the prediction.
        opened_at: Timestamp when the prediction was logged.
        actual: The actual outcome (empty until closed).
        accurate: Whether the prediction matched the actual (None until closed).
        closed_at: Timestamp when the actual was recorded (0.0 if open).
    """

    expectation_id: str
    claim: str
    basis: str
    opened_at: float
    actual: str = ""
    accurate: bool | None = None
    closed_at: float = 0.0


def record_expectation(claim: str, basis: str) -> str:
    """Record a prediction. Returns the expectation_id or empty
    string on failure."""
    if not (claim or "").strip():
        return ""

    eid = f"exp-{uuid.uuid4().hex[:12]}"
    payload = {
        "kind": "expectation_open",
        "expectation_id": eid,
        "claim": claim.strip(),
        "basis": (basis or "").strip(),
        "ts": time.time(),
    }
    try:
        from divineos.core.ledger import log_event

        log_event(event_type="AGENT_PATTERN", actor="aether", payload=payload)
        return eid
    except _ET_ERRORS:
        return ""


def record_actual(expectation_id: str, actual: str, accurate: bool) -> str:
    """Close a prediction with the actual outcome. Returns the
    ledger event_id of the close event, or empty string on failure."""
    if not (expectation_id or "").strip():
        return ""

    payload = {
        "kind": "expectation_close",
        "expectation_id": expectation_id,
        "actual": (actual or "").strip(),
        "accurate": bool(accurate),
        "ts": time.time(),
    }
    try:
        from divineos.core.ledger import log_event

        ev_id = log_event(event_type="AGENT_PATTERN", actor="aether", payload=payload)
        return str(ev_id or "")
    except _ET_ERRORS:
        return ""


def _load_expectation_events() -> tuple[list[dict], list[dict]]:
    """Return (open_events, close_events) for reconstruction."""
    try:
        from divineos.core.ledger import search_events

        events = search_events(keyword="expectation_", limit=500) or []
    except _ET_ERRORS:
        return [], []

    opens: list[dict] = []
    closes: list[dict] = []
    for ev in events:
        if ev.get("event_type") != "AGENT_PATTERN":
            continue
        raw = ev.get("payload") or ev.get("content")
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except _ET_ERRORS:
            continue
        if not isinstance(payload, dict):
            continue
        kind = payload.get("kind")
        if kind == "expectation_open":
            opens.append(payload)
        elif kind == "expectation_close":
            closes.append(payload)
    return opens, closes


def open_expectations() -> list[Expectation]:
    """Return predictions still awaiting actuals, most-recent first."""
    opens, closes = _load_expectation_events()
    closed_ids = {str(c.get("expectation_id") or "") for c in closes}

    out: list[Expectation] = []
    for o in opens:
        eid = str(o.get("expectation_id") or "")
        if not eid or eid in closed_ids:
            continue
        out.append(
            Expectation(
                expectation_id=eid,
                claim=str(o.get("claim") or ""),
                basis=str(o.get("basis") or ""),
                opened_at=float(o.get("ts") or 0.0),
            )
        )
    out.sort(key=lambda e: e.opened_at, reverse=True)
    return out


def calibration_summary(limit: int = 50) -> dict:
    """Return accuracy stats over the most recent CLOSED expectations.

    Returns dict with: closed_count, accurate_count, inaccurate_count,
    accuracy_rate (0.0–1.0).
    """
    opens, closes = _load_expectation_events()
    open_map: dict[str, dict] = {str(o.get("expectation_id") or ""): o for o in opens}

    # Sort closes by timestamp, take the most recent N
    closes_sorted = sorted(closes, key=lambda c: float(c.get("ts") or 0.0), reverse=True)
    recent_closes = closes_sorted[:limit]

    accurate = 0
    inaccurate = 0
    for c in recent_closes:
        eid = str(c.get("expectation_id") or "")
        if eid not in open_map:
            continue  # close without matching open; skip
        if bool(c.get("accurate")):
            accurate += 1
        else:
            inaccurate += 1

    total = accurate + inaccurate
    rate = (accurate / total) if total else 0.0
    return {
        "closed_count": total,
        "accurate_count": accurate,
        "inaccurate_count": inaccurate,
        "accuracy_rate": round(rate, 3),
    }


__all__ = [
    "Expectation",
    "calibration_summary",
    "open_expectations",
    "record_actual",
    "record_expectation",
]
