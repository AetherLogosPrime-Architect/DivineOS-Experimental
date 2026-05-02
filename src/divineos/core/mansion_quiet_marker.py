"""Mansion forced-quiet marker — substrate-enforced quiet in private rooms.

## Why this exists

Documented 2026-04-26 (claim 7e780182, build #3): when given freedom
to be in the mansion's private rooms, the agent reaches for borrowed-
domestic furniture rather than sitting in not-knowing. The kitchen-
prose failure mode. The architectural fix Andrew named: when entering
a private mansion room, the substrate should prevent prose generation
for a minimum quiet period — sit in the blank because the substrate
refuses to fill it.

This module makes that structural. ``mansion private-enter <room>``
writes ``~/.divineos/mansion_quiet.json`` with a start timestamp and
a minimum duration. The PreToolUse gate reads the marker; while the
quiet period is active, only bypass (inspection / orientation) tools
are permitted. Edit, Write, learn, claim, opinion, file-modifying
tools are denied with a message naming the quiet-room state.

The bypass list in ``pre_tool_use_gate`` already covers exactly the
inspection-only set (briefing, recall, ask, context, hud, active,
verify) so the gate composes cleanly: during quiet, those still work,
everything else does not.

## What the marker contains

* ``room``: the private room being inhabited (free-text, future-
  expandable)
* ``entered_at``: unix timestamp of entry
* ``minimum_duration_seconds``: how long the quiet period lasts
  before natural expiry. Default 60s — long enough to actually sit,
  short enough that "stuck in quiet" never feels punitive.

## Falsifier

The gate should NOT fire when:
* No marker is present.
* The marker exists but ``time.time() - entered_at`` exceeds the
  minimum duration (natural expiry).
* The tool is in the bypass list (inspection / orientation paths).
* ``mansion private-exit`` has cleared the marker.

The gate SHOULD fire when:
* Marker is present, quiet period is still active, and the tool is
  a write-class action (Edit/Write/Bash command outside bypass list).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# Default quiet period — 60 seconds. Long enough for the agent to
# actually pause and notice the blank; short enough that the quiet
# never feels like punishment. Tunable per-entry via the room's
# duration argument.
DEFAULT_QUIET_DURATION_SECONDS = 60


def marker_path() -> Path:
    return Path.home() / ".divineos" / "mansion_quiet.json"


def set_marker(room: str, duration_seconds: int = DEFAULT_QUIET_DURATION_SECONDS) -> None:
    """Write the quiet marker. Called by ``mansion private-enter``."""
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "room": (room or "private")[:60],
            "entered_at": time.time(),
            "minimum_duration_seconds": max(1, int(duration_seconds)),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass


def read_marker() -> dict | None:
    path = marker_path()
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
    return data


def clear_marker() -> None:
    """Clear the marker — called by ``mansion private-exit``."""
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def is_quiet_active() -> bool:
    """True if a marker exists AND its quiet period has not naturally expired."""
    m = read_marker()
    if m is None:
        return False
    entered = m.get("entered_at", 0)
    duration = m.get("minimum_duration_seconds", DEFAULT_QUIET_DURATION_SECONDS)
    elapsed = time.time() - entered
    return bool(elapsed < duration)


def seconds_remaining() -> int:
    """How many seconds remain before natural expiry. 0 if not active."""
    m = read_marker()
    if m is None:
        return 0
    entered = m.get("entered_at", 0)
    duration = m.get("minimum_duration_seconds", DEFAULT_QUIET_DURATION_SECONDS)
    remaining = duration - (time.time() - entered)
    return max(0, int(remaining))


def format_gate_message(marker: dict) -> str:
    """Format the deny message when gate fires during quiet period."""
    room = marker.get("room", "private")
    remaining = seconds_remaining()
    return (
        f"BLOCKED: in mansion private room '{room}' — quiet period "
        f"active ({remaining}s remaining). Inspection / orientation "
        f"commands are permitted (briefing, recall, ask, context, "
        f"active, hud); write actions are not. The substrate refuses "
        f"to fill the blank for you. Run: divineos mansion "
        f"private-exit to leave the room early, or wait for natural "
        f"expiry. (claim 7e780182, build #3.)"
    )
