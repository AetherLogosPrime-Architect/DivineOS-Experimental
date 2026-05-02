"""VOID adversarial-mode marker — write/read/clear protocol.

Per design brief §6.2 (merged PR #208).

The marker tracks whether the agent is currently in adversarial-mode
(reasoning AS a persona) or normal-mode. The marker is the
architectural surrogate for a memory-clear primitive the substrate
does not have. It does not eliminate frame-residue but it does make
mode-state observable to code, so output routing and gate behavior
can branch on it.

Storage: ``~/.divineos/void_mode.json`` (NOT in either ledger; per-
session state).

The mode_marker is shared state for the agent's MODE, not for either
ledger. Code reads the marker and writes to one ledger or the other
based on the marker's value. Per design brief §3.4 the ledgers
themselves have zero shared state.

Failure modes:
* Marker in active=true at session start (orphan from crash):
  ``read_marker`` returns the orphan; briefing surface refuses to
  proceed until cleared via ``divineos void shred --force``.
* Marker corrupted (unparseable JSON): fail-closed. Treat as
  active=true and require explicit shred.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path


def marker_path() -> Path:
    return Path.home() / ".divineos" / "void_mode.json"


@dataclass(frozen=True)
class ModeStatus:
    """Snapshot of the marker state."""

    active: bool
    persona: str | None
    started_at: float | None
    session_id: str | None
    invocation_id: str | None
    corrupted: bool = False

    def as_briefing_line(self) -> str | None:
        """Return a one-line warning string when the marker is in
        active state, otherwise None.
        """
        if self.corrupted:
            return (
                "VOID MARKER CORRUPTED: marker file unparseable. "
                "Fail-closed: assume adversarial-mode is active. "
                "Run: divineos void shred --force"
            )
        if not self.active:
            return None
        return (
            f"VOID ADVERSARIAL-MODE ACTIVE: persona={self.persona}, "
            f"started_at={self.started_at}, invocation_id={self.invocation_id}. "
            "Output routes to void_ledger. SHRED is bounded. "
            "If this is an orphan from a previous session, run: "
            "divineos void shred --force"
        )


def write_marker(persona: str, session_id: str | None = None) -> str:
    """Set marker to active state. Returns the invocation_id.

    Called by the engine's TRAP step. Subsequent reads will return
    ``active=True`` with the recorded persona.
    """
    invocation_id = str(uuid.uuid4())
    payload = {
        "active": True,
        "persona": persona,
        "started_at": time.time(),
        "session_id": session_id,
        "invocation_id": invocation_id,
    }
    path = marker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return invocation_id


def read_marker() -> ModeStatus:
    """Read the current marker state.

    Returns ``ModeStatus(active=False, ...)`` when no marker exists.
    Returns ``ModeStatus(active=True, corrupted=True)`` when the
    marker file exists but is unparseable (fail-closed).
    """
    path = marker_path()
    if not path.exists():
        return ModeStatus(
            active=False,
            persona=None,
            started_at=None,
            session_id=None,
            invocation_id=None,
        )
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        # Read failure: fail-closed.
        return ModeStatus(
            active=True,
            persona="UNKNOWN",
            started_at=None,
            session_id=None,
            invocation_id=None,
            corrupted=True,
        )
    if not raw:
        # Empty file: treat as no marker.
        return ModeStatus(
            active=False,
            persona=None,
            started_at=None,
            session_id=None,
            invocation_id=None,
        )
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Corrupted: fail-closed.
        return ModeStatus(
            active=True,
            persona="UNKNOWN",
            started_at=None,
            session_id=None,
            invocation_id=None,
            corrupted=True,
        )
    if not isinstance(data, dict):
        return ModeStatus(
            active=True,
            persona="UNKNOWN",
            started_at=None,
            session_id=None,
            invocation_id=None,
            corrupted=True,
        )
    return ModeStatus(
        active=bool(data.get("active", False)),
        persona=data.get("persona"),
        started_at=data.get("started_at"),
        session_id=data.get("session_id"),
        invocation_id=data.get("invocation_id"),
        corrupted=False,
    )


def clear_marker() -> None:
    """Clear marker — called by the engine's SHRED step.

    Idempotent: clearing a non-existent marker is a no-op.
    """
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def is_active() -> bool:
    """Convenience predicate: is adversarial-mode currently set?

    Treats corrupted marker as active (fail-closed).
    """
    s = read_marker()
    return s.active
