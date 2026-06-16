"""Unified gate marker schema — the foundation primitive for signal-based gates.

Step 0 of the signal-based-gates redesign
(docs/signal-based-gates-design-2026-06-16.md). This module provides a single
canonical schema and I/O contract for every gate marker in the OS, so the
gate stack stops fragmenting across ad-hoc marker files with subtly-different
shapes.

The schema (per the design doc's five primitives):

    GateMarker(
        event_type,           # "hedge_fire", "correction_filed", etc.
        triggered_at,         # unix timestamp
        triggering_evidence,  # the evidence supporting the gate's claim
        resolution_action,    # CLI command that clears the marker
        session_id,           # session within which this marker was created
    )

Path layout:

    <DIVINEOS_HOME>/gate_markers/<event_type>__<short_id>.json

Single shape, many event types. The Step 0 migration moves the existing
correctly-shaped gates (hedge-unresolved, correction-not-logged, pull-
detection) onto this schema as a no-op refactor (semantic equivalence
verified by test_gate_marker_equivalence.py). Count-based gate migrations
come AFTER Step 0 lands clean.

Architectural principle: a gate is correctly shaped if and only if it has
all five primitives (claim, event, resolution, marker, bypass). This module
provides the marker primitive. The other four primitives are per-gate.

See docs/signal-based-gates-design-2026-06-16.md for the full design.

The convergence-architecture catching its own shape: this module is itself
an instance of the claims-engine discipline applied to enforcement. Every
gate marker is a claim about state; every claim requires evidence; the
GateMarker dataclass is the canonical evidence carrier.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from divineos.core.atomic_io import atomic_write_text
from divineos.core.paths import divineos_home


@dataclass(frozen=True)
class GateMarker:
    """A gate's claim about state, backed by direct evidence.

    All five fields are required. A marker without ``triggering_evidence``
    is theater; without ``resolution_action`` is a trap; without
    ``session_id`` cannot be scoped across the digital-mitosis boundary.

    The fields are immutable (frozen=True) — once a marker is written, its
    contents do not change. Resolution = file removal, not field mutation.
    """

    event_type: str
    triggered_at: float
    triggering_evidence: str
    resolution_action: str
    session_id: str


_MARKERS_DIR_NAME = "gate_markers"


def gate_markers_dir() -> Path:
    """Return the gate-markers directory under DIVINEOS_HOME.

    Does NOT create the directory; callers that need write access should
    ensure it exists via ``gate_markers_dir().mkdir(parents=True,
    exist_ok=True)`` or rely on ``write_marker`` which handles creation.
    """
    return divineos_home() / _MARKERS_DIR_NAME


def _short_id() -> str:
    """Generate a short unique id for marker disambiguation.

    Uses the first 8 hex chars of a uuid4 — collision-resistant enough
    for marker filenames where the event_type prefix already namespaces.
    """
    return uuid.uuid4().hex[:8]


def _marker_filename(event_type: str, short_id: str) -> str:
    """Compose a marker filename from its event_type and short_id.

    Format: ``<event_type>__<short_id>.json``. The double underscore is
    the separator so glob patterns (``<event_type>__*.json``) can locate
    all markers of a given event_type without filename ambiguity if an
    event_type ever contains an underscore.
    """
    return f"{event_type}__{short_id}.json"


def write_marker(
    event_type: str,
    triggering_evidence: str,
    resolution_action: str,
    session_id: str,
    triggered_at: float | None = None,
) -> Path:
    """Write a gate marker. Returns the path it was written to.

    ``triggered_at`` defaults to ``time.time()``; pass an explicit value
    only for tests or for replaying historical events. The function
    creates the gate_markers directory if it does not exist.

    Fail-open: if the write fails (disk full, permission denied, etc.),
    the exception propagates. Callers in hook context should wrap in
    try/except per the existing marker pattern; callers in normal code
    paths should let the exception surface so the failure is visible
    rather than silent.

    Returns the Path the marker was written to. The path encodes both
    the event_type (for glob-based lookup) and a short_id (for
    disambiguation when multiple markers of the same event_type can
    coexist — e.g. multiple hedge fires within a session).
    """
    if triggered_at is None:
        triggered_at = time.time()
    marker = GateMarker(
        event_type=event_type,
        triggered_at=triggered_at,
        triggering_evidence=triggering_evidence,
        resolution_action=resolution_action,
        session_id=session_id,
    )
    short_id = _short_id()
    path = gate_markers_dir() / _marker_filename(event_type, short_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(asdict(marker)))
    return path


def read_marker(path: Path) -> GateMarker | None:
    """Read a specific marker by path. Returns None if absent or unreadable.

    Fail-open on JSON decode error, missing fields, wrong type — None is
    returned and the caller can treat as "no marker found." Logging
    a corrupt-marker event for later investigation is the caller's
    responsibility if they want it.
    """
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    # Validate all required fields are present.
    required = {"event_type", "triggered_at", "triggering_evidence", "resolution_action", "session_id"}
    if not required.issubset(data.keys()):
        return None
    try:
        return GateMarker(
            event_type=str(data["event_type"]),
            triggered_at=float(data["triggered_at"]),
            triggering_evidence=str(data["triggering_evidence"]),
            resolution_action=str(data["resolution_action"]),
            session_id=str(data["session_id"]),
        )
    except (TypeError, ValueError):
        return None


def find_markers(event_type: str) -> list[Path]:
    """Return all marker paths for a given event_type, sorted oldest-first.

    Sorting is by ``triggered_at`` from the marker payload. Markers that
    fail to read are skipped silently — they may be corrupt or partially
    written; the caller handles the missing-data case by getting fewer
    paths back than expected, not by exception.

    Returns an empty list if the gate_markers directory does not exist
    OR if no markers of the given event_type are present.
    """
    directory = gate_markers_dir()
    if not directory.exists():
        return []
    matches = list(directory.glob(f"{event_type}__*.json"))
    # Sort by triggered_at from marker contents — filesystem mtime is
    # less reliable across copies/syncs.
    decorated: list[tuple[float, Path]] = []
    for p in matches:
        marker = read_marker(p)
        if marker is not None:
            decorated.append((marker.triggered_at, p))
    decorated.sort(key=lambda pair: pair[0])
    return [p for _, p in decorated]


def is_active(event_type: str) -> bool:
    """Return True if at least one marker of the given event_type exists.

    The gate-fires-when-event-occurred check. Equivalent to
    ``len(find_markers(event_type)) > 0`` but cheaper because it can
    short-circuit on the first match.
    """
    directory = gate_markers_dir()
    if not directory.exists():
        return False
    for p in directory.glob(f"{event_type}__*.json"):
        if read_marker(p) is not None:
            return True
    return False


def clear_marker(path: Path) -> None:
    """Remove a specific marker. No-op if it does not exist."""
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def clear_all(event_type: str) -> int:
    """Remove all markers of a given event_type. Returns count cleared.

    Used by resolution-action commands that discharge the gate — e.g.
    ``divineos claim`` clears all hedge_fire markers, ``divineos learn``
    clears all correction_filed_unlogged markers.
    """
    cleared = 0
    for p in find_markers(event_type):
        clear_marker(p)
        cleared += 1
    return cleared


__all__ = [
    "GateMarker",
    "clear_all",
    "clear_marker",
    "find_markers",
    "gate_markers_dir",
    "is_active",
    "read_marker",
    "write_marker",
]
