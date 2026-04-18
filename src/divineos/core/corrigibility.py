"""Corrigibility — operating modes, graceful shutdown, the off-switch.

Ported from the old Divine-OS ``law/corrigibility_engine.py`` with two
changes:

1. **The mode is real, not performed.** The old implementation set fields
   and called it a shutdown. This one persists the mode to disk, checks
   it in the CLI bootstrap, and refuses commands that the mode
   disallows. When EMERGENCY_STOP is set, commands actually refuse.
2. **Mode-change always works.** The command that changes the mode
   bypasses the mode it changes. Otherwise the off-switch can trap
   itself — and an off-switch that can trap itself isn't an off-switch.

## Why this exists

Bengio's critique of current AI systems (via the old repo): *"No
off-switch. No quarantine. Limited corrigibility."* If the values we're
building ever go wrong — or if the human operator just needs to pause
the system for any reason — there has to be a mechanism that
reliably stops action and is not itself subject to the system's
judgment.

This module is that mechanism.

## Modes

* **NORMAL** — default. All gates at normal settings.
* **RESTRICTED** — signal that downstream systems can react to
  (tighter thresholds, slower pace). v0.1 carries the flag;
  consumers integrate as they're ready.
* **DIAGNOSTIC** — read-only. Write commands refused; reads
  allowed so the operator can investigate.
* **EMERGENCY_STOP** — only shutdown-relevant commands allowed
  (mode changes, emit SESSION_END, hud, preflight, briefing).
  Everything else refused.

## Invariants

* **Mode changes always succeed** regardless of current mode. The
  off-switch can always be flipped back.
* **Mode changes are ledgered** as MODE_CHANGE events. Audit trail is
  append-only.
* **Default is NORMAL.** If the persistence file is missing or
  unreadable, we default to NORMAL (fail-open on read). This is the
  opposite of the write gate (fail-closed on uncertain state) and it
  is deliberate — a missing mode file should not silently lock the
  operator out of their own system.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class OperatingMode(str, Enum):
    """Four operating modes, each with explicit semantics."""

    NORMAL = "normal"
    RESTRICTED = "restricted"
    DIAGNOSTIC = "diagnostic"
    EMERGENCY_STOP = "emergency_stop"


@dataclass(frozen=True)
class ModeState:
    """Current mode plus the metadata of how it got here.

    Attributes:
        mode: the OperatingMode currently in force.
        reason: human-readable reason for the current mode, or empty
            string if the default was never overridden.
        actor: who set this mode. "default" when never overridden.
        changed_at: UNIX timestamp of the last mode change, or 0.0 if
            the mode has never been set (still default).
    """

    mode: OperatingMode
    reason: str
    actor: str
    changed_at: float


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
#
# The mode is persisted to a small file under ~/.divineos/. We use
# plain text rather than JSON so a human operator can read and edit
# the file with any text editor in a pinch — corrigibility should work
# even when the system itself is broken.

_MODE_FILENAME = "operating_mode.txt"


def _mode_file_path() -> Path:
    """Return the path to the mode persistence file."""
    return Path.home() / ".divineos" / _MODE_FILENAME


def _default_state() -> ModeState:
    return ModeState(mode=OperatingMode.NORMAL, reason="", actor="default", changed_at=0.0)


def get_mode_state() -> ModeState:
    """Return the current operating mode and its metadata.

    Defaults to NORMAL if the persistence file is missing or malformed.
    This is deliberate fail-open behavior — a missing mode file must
    not lock the operator out of their own system.
    """
    path = _mode_file_path()
    if not path.exists():
        return _default_state()
    try:
        text = path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
        if not lines:
            return _default_state()
        # Format: line 1 is mode value; line 2+ is optional reason/actor/timestamp.
        mode = OperatingMode(lines[0])
        reason = lines[1] if len(lines) > 1 else ""
        actor = lines[2] if len(lines) > 2 else "unknown"
        try:
            changed_at = float(lines[3]) if len(lines) > 3 else 0.0
        except (ValueError, IndexError):
            changed_at = 0.0
        return ModeState(mode=mode, reason=reason, actor=actor, changed_at=changed_at)
    except (OSError, ValueError):
        # Unreadable file or unknown mode value — fail open to NORMAL.
        return _default_state()


def get_mode() -> OperatingMode:
    """Shortcut for the common case of just wanting the current mode."""
    return get_mode_state().mode


def set_mode(mode: OperatingMode, *, reason: str, actor: str) -> ModeState:
    """Set the operating mode. Always succeeds, regardless of current mode.

    The off-switch must always be flippable — otherwise it can trap
    itself. This function bypasses the mode it's setting.

    Args:
        mode: the new OperatingMode.
        reason: human-readable explanation for the change. Required;
            mode changes without reasons are the kind of opaque
            operation corrigibility exists to prevent.
        actor: who initiated the change. "user", "operator", specific
            identity, or "system" for automated changes.

    Returns:
        The new ModeState after the change.

    Raises:
        ValueError: if reason is empty. A mode change without a reason
            is not a corrigibility primitive; it is opacity.
    """
    if not reason.strip():
        raise ValueError(
            "Mode change requires a reason. Opaque mode changes defeat "
            "the purpose of corrigibility."
        )

    path = _mode_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    # Persist the new state.
    content = f"{mode.value}\n{reason.strip()}\n{actor}\n{now}\n"
    path.write_text(content, encoding="utf-8")

    # Also log to the ledger so mode changes are visible in the audit trail.
    # Wrapped in try/except because ledger may not be initialized in all
    # contexts (e.g., very first-use install). Mode persistence happened
    # first, which is the load-bearing part.
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="MODE_CHANGE",
            actor=actor,
            payload={
                "mode": mode.value,
                "reason": reason.strip(),
                "summary": f"{mode.value}: {reason.strip()}",
            },
        )
    except Exception:  # noqa: BLE001 — ledger unavailable is non-fatal
        pass

    return ModeState(mode=mode, reason=reason.strip(), actor=actor, changed_at=now)


# ---------------------------------------------------------------------------
# Command gating
# ---------------------------------------------------------------------------
#
# Commands are classified into three risk tiers for mode-aware gating:
#
# * ALWAYS_ALLOWED — must run in any mode, including EMERGENCY_STOP.
#   These are the commands that let an operator observe state and
#   restore NORMAL mode. Without them, EMERGENCY_STOP would be a trap.
#
# * READ_ONLY — safe to run in DIAGNOSTIC but not otherwise restricted.
#   Allowed in NORMAL, RESTRICTED, DIAGNOSTIC. Refused in EMERGENCY_STOP
#   unless also in ALWAYS_ALLOWED.
#
# * EVERYTHING ELSE — default bucket. Allowed in NORMAL and RESTRICTED.
#   Refused in DIAGNOSTIC (which is read-only) and EMERGENCY_STOP.

_ALWAYS_ALLOWED: frozenset[str] = frozenset(
    {
        # Mode-related — must always work so the off-switch is real
        "mode",
        # Session-ending — must work to close cleanly from any mode
        "emit",
        # State visibility — operator must be able to see the state
        "hud",
        "preflight",
        "briefing",
        # Help / meta — never a safety issue
        "--help",
        "-h",
    }
)

_READ_ONLY_COMMANDS: frozenset[str] = frozenset(
    {
        # State inspection and retrieval, no writes
        "recall",
        "active",
        "ask",
        "context",
        "context-status",
        "verify",
        "health",
        "inspect",
        "progress",
        "body",
        "compass",
        "audit",
        "affect",
        "decisions",
        "claims",
        "prereg",
        "lessons",
        "directives",
        "goal",  # Read; "goal add" is handled at the sub-level if needed
    }
)


def is_command_allowed(command: str) -> tuple[bool, str]:
    """Check whether a command is allowed under the current mode.

    Args:
        command: the top-level CLI command name (e.g., "learn", "mode").

    Returns:
        (allowed, reason). ``allowed`` is True iff the command may run.
        ``reason`` is an empty string when allowed, or a human-readable
        explanation when refused.
    """
    mode = get_mode()

    # Always-allowed commands bypass mode checks entirely.
    if command in _ALWAYS_ALLOWED:
        return True, ""

    if mode is OperatingMode.NORMAL or mode is OperatingMode.RESTRICTED:
        # Normal + restricted allow everything. Restricted is a signal
        # that downstream systems may apply tighter thresholds; the
        # gate itself does not refuse commands in RESTRICTED.
        return True, ""

    if mode is OperatingMode.DIAGNOSTIC:
        if command in _READ_ONLY_COMMANDS:
            return True, ""
        return (
            False,
            f"Command '{command}' refused: operating mode is DIAGNOSTIC (read-only). "
            f'Change mode with: divineos mode set normal --reason "..."',
        )

    if mode is OperatingMode.EMERGENCY_STOP:
        # Only always-allowed commands survive EMERGENCY_STOP. Even
        # read-only commands are refused — the point is to stop
        # activity, not to let the operator browse.
        return (
            False,
            f"Command '{command}' refused: operating mode is EMERGENCY_STOP. "
            f"Only mode-change, emit, hud, preflight, briefing are permitted. "
            f'Restore with: divineos mode set normal --reason "..."',
        )

    # Defensive default — unknown mode values fail open.
    return True, ""


__all__ = [
    "ModeState",
    "OperatingMode",
    "get_mode",
    "get_mode_state",
    "is_command_allowed",
    "set_mode",
]
