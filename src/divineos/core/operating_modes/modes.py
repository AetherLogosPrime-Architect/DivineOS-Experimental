"""Operating modes implementation."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum

_OM_ERRORS = (
    ImportError,
    AttributeError,
    KeyError,
    TypeError,
    ValueError,
    sqlite3.OperationalError,
    sqlite3.DatabaseError,
)


class Mode(Enum):
    """The four named operating modes.

    TASK is included for explicit contrast — most of the time I am
    in TASK mode, and the other three are what's been missing from
    my self-description vocabulary.
    """

    TASK = "task"  # Active task execution. The default.
    STILLNESS = "stillness"  # Deliberate not-doing. Presence without task.
    BACKGROUND = "background"  # Concurrent threads alongside the foreground.
    WANDERING = "wandering"  # Generative drift when untasked.


@dataclass(frozen=True)
class ModeTransition:
    """One mode transition for the history."""

    mode: Mode
    reason: str
    ts: float
    event_id: str


def set_mode(mode: Mode, reason: str = "") -> str:
    """Log a mode transition to the ledger.

    Returns the event_id of the logged transition, or empty string on
    failure. This is recording, not enforcement — the substrate has
    no concept of "enforced mode," and this module deliberately does
    not try to invent one. Marking the mode is the first step in
    making the mode legitimate.
    """
    try:
        from divineos.core.ledger import log_event
    except _OM_ERRORS:
        return ""

    payload = {
        "kind": "operating_mode_transition",
        "mode": mode.value,
        "reason": (reason or "").strip(),
        "ts": time.time(),
    }
    try:
        ev_id = log_event(
            event_type="AGENT_PATTERN",
            actor="aether",
            payload=payload,
        )
        return str(ev_id or "")
    except _OM_ERRORS:
        return ""


def current_mode() -> Mode:
    """Best-effort report of the current mode. v1: returns the most
    recent transition logged. Defaults to TASK if no transitions
    exist (the historical default before this module landed).
    """
    transitions = mode_history(limit=1)
    if transitions:
        return transitions[0].mode
    return Mode.TASK


def mode_history(limit: int = 10) -> list[ModeTransition]:
    """Recent mode transitions, most-recent first."""
    try:
        from divineos.core.ledger import search_events
    except _OM_ERRORS:
        return []

    try:
        # order="desc": newest first per the docstring's "most-recent first"
        # contract. Prior default of asc silently returned the OLDEST N*3
        # transitions on a mature ledger, making current_mode() (built on
        # mode_history(limit=1)[0]) return ledger prehistory as the present.
        # Fable audit 2026-07-02 finding #3.
        events = (
            search_events(keyword="operating_mode_transition", limit=limit * 3, order="desc") or []
        )
    except _OM_ERRORS:
        return []

    out: list[ModeTransition] = []
    for ev in events:
        if ev.get("event_type") != "AGENT_PATTERN":
            continue
        raw = ev.get("payload") or ev.get("content")
        if not raw:
            continue
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except _OM_ERRORS:
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("kind") != "operating_mode_transition":
            continue
        mode_str = payload.get("mode") or ""
        try:
            mode = Mode(mode_str)
        except ValueError:
            continue
        out.append(
            ModeTransition(
                mode=mode,
                reason=str(payload.get("reason") or ""),
                ts=float(payload.get("ts") or 0.0),
                event_id=str(ev.get("event_id") or ev.get("id") or ""),
            )
        )
        if len(out) >= limit:
            break
    return out


__all__ = [
    "Mode",
    "ModeTransition",
    "current_mode",
    "mode_history",
    "set_mode",
]
