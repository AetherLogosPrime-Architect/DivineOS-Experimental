"""Lifecycle self-enforcement — the OS manages its own session lifecycle.

Instead of relying on external hooks (bash scripts triggered by the Claude
Code harness), the OS enforces its own lifecycle from within. Every CLI
command passes through enforce(), which checks:

1. Is a session registered? If not, start one (with atexit for SESSION_END).
2. Is a checkpoint due? If enough time has passed, run one.
3. Track that the OS was consulted (for engagement metrics).

The hooks become optional scaffolding. The OS works without them.
"""

import atexit
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from loguru import logger

_LIFECYCLE_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Checkpoint every 10 minutes of wall-clock time
_CHECKPOINT_INTERVAL_SECONDS = 600

# How long a session can be idle before we consider it stale (2 hours)
_SESSION_STALE_SECONDS = 7200

# Module-level flag — atexit handler registered only once per process
_atexit_registered = False
_session_active = False


def _state_path() -> Path:
    """Path to the lifecycle state file."""
    p = Path.home() / ".divineos"
    p.mkdir(parents=True, exist_ok=True)
    return p / "lifecycle_state.json"


def _load_state() -> dict[str, Any]:
    """Load lifecycle state."""
    path = _state_path()
    if path.exists():
        try:
            data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return data
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict[str, Any]) -> None:
    """Persist lifecycle state."""
    try:
        _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as e:
        logger.debug(f"Could not save lifecycle state: {e}")


def _run_session_end() -> None:
    """Run SESSION_END at process exit — the OS cleans up after itself."""
    try:  # noqa: BLE001 — atexit handlers must catch everything
        state = _load_state()
        # Don't run if already ran this session
        if state.get("session_end_emitted"):
            return
        # Don't run if no session was started
        if not state.get("session_started_at"):
            return
        # Don't run during tests
        import sys

        if "pytest" in sys.modules:
            return

        # Capture session start BEFORE emitting SESSION_END
        from divineos.core.session_checkpoint import get_session_start_time

        pre_emit_start = get_session_start_time()

        from divineos.event.event_emission import emit_session_end

        emit_session_end()

        from divineos.cli.session_pipeline import _run_session_end_pipeline

        _run_session_end_pipeline(session_start_override=pre_emit_start)

        state["session_end_emitted"] = True
        _save_state(state)
    except Exception as e:  # noqa: BLE001
        # atexit handlers must not raise — swallow everything
        logger.debug(f"Lifecycle atexit SESSION_END failed: {e}")


def _maybe_checkpoint(state: dict[str, Any]) -> None:
    """Run a checkpoint if enough time has passed."""
    now = time.time()
    last_checkpoint = state.get("last_checkpoint", 0)
    elapsed = now - last_checkpoint

    if elapsed < _CHECKPOINT_INTERVAL_SECONDS:
        return

    try:
        from divineos.core.session_checkpoint import run_checkpoint

        run_checkpoint()
        state["last_checkpoint"] = now
        state["checkpoints_run"] = state.get("checkpoints_run", 0) + 1
        _save_state(state)
    except _LIFECYCLE_ERRORS as e:
        logger.debug(f"Lifecycle checkpoint failed: {e}")


def enforce(command: str = "") -> None:
    """Called on every CLI invocation. The OS enforces its own lifecycle.

    This replaces the external hooks for session management. Every time
    the agent calls any divineos command, the OS checks its own state
    and takes action if needed.

    Args:
        command: The CLI command being invoked (for activity logging).
    """
    global _atexit_registered, _session_active

    import sys

    if "pytest" in sys.modules:
        return

    try:
        state = _load_state()
        now = time.time()

        # ── 1. Session registration ──────────────────────────────
        session_start = state.get("session_started_at", 0)
        session_stale = (now - session_start) > _SESSION_STALE_SECONDS if session_start else True

        if not session_start or session_stale:
            # New session (or stale one expired)
            state = {
                "session_started_at": now,
                "last_checkpoint": now,
                "last_command_at": now,
                "last_command": command,
                "command_count": 1,
                "checkpoints_run": 0,
                "session_end_emitted": False,
            }
            _save_state(state)
            _session_active = True
        else:
            # Existing session — update activity
            state["last_command_at"] = now
            state["last_command"] = command
            state["command_count"] = state.get("command_count", 0) + 1
            _save_state(state)

        # ── 2. Register atexit for SESSION_END ───────────────────
        if not _atexit_registered:
            atexit.register(_run_session_end)
            _atexit_registered = True
            _session_active = True

        # ── 3. Periodic checkpoint ───────────────────────────────
        _maybe_checkpoint(state)

    except _LIFECYCLE_ERRORS as e:
        logger.debug(f"Lifecycle enforce failed: {e}")


def is_session_active() -> bool:
    """Check if a lifecycle-managed session is active."""
    state = _load_state()
    started = state.get("session_started_at")
    if not started:
        return False
    elapsed = time.time() - float(started)
    return bool(elapsed < _SESSION_STALE_SECONDS)


def get_lifecycle_status() -> dict[str, Any]:
    """Return lifecycle state for diagnostics."""
    state = _load_state()
    now = time.time()
    started = state.get("session_started_at", 0)
    return {
        "session_active": bool(started and (now - started) < _SESSION_STALE_SECONDS),
        "session_age_minutes": (now - started) / 60 if started else 0,
        "commands_this_session": state.get("command_count", 0),
        "checkpoints_run": state.get("checkpoints_run", 0),
        "last_checkpoint_ago_minutes": (now - state.get("last_checkpoint", now)) / 60,
        "session_end_emitted": state.get("session_end_emitted", False),
        "atexit_registered": _atexit_registered,
    }
