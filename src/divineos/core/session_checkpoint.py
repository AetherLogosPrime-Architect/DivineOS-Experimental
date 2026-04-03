"""Session Checkpoint — Lightweight periodic saves during work.

The full SESSION_END pipeline is heavy: analysis, knowledge extraction,
maturity cycles, consolidation. It should run at session end.

Checkpoints are lighter: save handoff note, HUD snapshot, log to ledger.
They run periodically (every N edits) so state isn't lost if context
collapses before SESSION_END fires.

Also tracks tool call volume as a proxy for context usage, warning
when the session is approaching token limits.
"""

import json
import time
from divineos.core.hud import save_hud_snapshot
from divineos.core.hud_handoff import save_handoff_note
from divineos.core.hud_state import _ensure_hud_dir
from divineos.event.event_emission import emit_event
from pathlib import Path
from typing import Any

from loguru import logger


# ─── Counter File ─────────────────────────────────────────────────────


def _counter_path() -> Path:
    """Path to the per-session edit counter file."""
    p = Path.home() / ".divineos"
    p.mkdir(parents=True, exist_ok=True)
    return p / "checkpoint_state.json"


def _load_state() -> dict[str, Any]:
    """Load checkpoint tracking state."""
    path = _counter_path()
    if path.exists():
        try:
            result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            return result
        except (json.JSONDecodeError, OSError):
            pass
    return {
        "edits": 0,
        "tool_calls": 0,
        "last_checkpoint": 0.0,
        "checkpoints_run": 0,
        "session_start": time.time(),
    }


def _save_state(state: dict[str, Any]) -> None:
    """Persist checkpoint tracking state."""
    _counter_path().write_text(json.dumps(state, indent=2), encoding="utf-8")


def reset_state() -> None:
    """Reset counters — call at session start."""
    _save_state(
        {
            "edits": 0,
            "tool_calls": 0,
            "last_checkpoint": 0.0,
            "checkpoints_run": 0,
            "session_start": time.time(),
        }
    )


def get_session_start_time() -> float | None:
    """Get the Unix timestamp when the current session started.

    Uses the most recent SESSION_END in the ledger as the boundary
    (anything after it is the current session). Falls back to
    checkpoint state, then None.

    Prefers ledger over checkpoint state because compaction resets
    the conversation without resetting checkpoint_state.json —
    the ledger is always the source of truth for session boundaries.
    """
    # Primary: last SESSION_END in ledger = end of previous session = start of current
    try:
        from divineos.core.memory import _get_connection

        conn = _get_connection()
        try:
            row = conn.execute(
                "SELECT timestamp FROM system_events "
                "WHERE event_type = 'SESSION_END' "
                "ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            if row:
                return float(row[0])
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        pass

    # Fallback: checkpoint state (may be stale after compaction)
    state = _load_state()
    start = state.get("session_start")
    if start and isinstance(start, (int, float)):
        return float(start)

    return None


def increment_edit() -> dict[str, Any]:
    """Record an edit and return current state."""
    state = _load_state()
    state["edits"] = state.get("edits", 0) + 1
    state["tool_calls"] = state.get("tool_calls", 0) + 1
    _save_state(state)
    return state


def increment_tool_call() -> dict[str, Any]:
    """Record any tool call (for context monitoring)."""
    state = _load_state()
    state["tool_calls"] = state.get("tool_calls", 0) + 1
    _save_state(state)
    return state


# ─── Checkpoint Decision ──────────────────────────────────────────────

# Checkpoint every N edits. Not every tool call — edits are what change state.
CHECKPOINT_EDIT_THRESHOLD = 15

# Context usage warnings based on tool call count.
# Rough heuristic: each tool call ~ 1-3K tokens of context used.
# Claude context ~ 200K tokens. Conservative estimates:
CONTEXT_WARN_THRESHOLD = 150  # ~50% context used, gentle reminder
CONTEXT_URGENT_THRESHOLD = 250  # ~80% context, save NOW
CONTEXT_CRITICAL_THRESHOLD = 350  # ~90% context, session ending soon


def should_checkpoint(state: dict[str, Any]) -> bool:
    """True if enough edits have accumulated since last checkpoint."""
    edits = state.get("edits", 0)
    checkpoints_run = state.get("checkpoints_run", 0)
    edits_since = edits - (checkpoints_run * CHECKPOINT_EDIT_THRESHOLD)
    return bool(edits_since >= CHECKPOINT_EDIT_THRESHOLD)


def context_warning_level(state: dict[str, Any]) -> str:
    """Return context usage warning level: 'ok', 'warn', 'urgent', 'critical'."""
    calls = state.get("tool_calls", 0)
    if calls >= CONTEXT_CRITICAL_THRESHOLD:
        return "critical"
    if calls >= CONTEXT_URGENT_THRESHOLD:
        return "urgent"
    if calls >= CONTEXT_WARN_THRESHOLD:
        return "warn"
    return "ok"


def format_context_warning(state: dict[str, Any]) -> str | None:
    """Format a human-readable context warning, or None if all clear."""
    level = context_warning_level(state)
    calls = state.get("tool_calls", 0)
    edits = state.get("edits", 0)
    checkpoints = state.get("checkpoints_run", 0)

    if level == "ok":
        return None

    base = f"[Context Monitor] {calls} tool calls, {edits} edits, {checkpoints} checkpoints"

    if level == "warn":
        return (
            f"{base}\n"
            "Context usage ~50%. Consider running 'divineos emit SESSION_END' "
            "to save knowledge before compaction."
        )
    if level == "urgent":
        return (
            f"{base}\n"
            "CONTEXT USAGE HIGH (~80%). Run 'divineos emit SESSION_END' NOW "
            "to extract knowledge. Session will compact soon."
        )
    if level == "critical":
        return (
            f"{base}\n"
            "CRITICAL: Context nearly full (~90%). "
            "Run 'divineos emit SESSION_END' IMMEDIATELY. "
            "Context compaction is imminent — unsaved work will be summarized away."
        )
    return None


# ─── Run Checkpoint ───────────────────────────────────────────────────


def run_checkpoint() -> str:
    """Run a lightweight checkpoint — save state without full pipeline.

    Returns a summary string of what was saved.
    """
    parts: list[str] = []

    # 1. Save HUD snapshot
    try:
        save_hud_snapshot()
        parts.append("HUD snapshot saved")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: HUD snapshot failed: %s", e)

    # 2. Save handoff note with current goals
    try:
        goals_path = _ensure_hud_dir() / "active_goals.json"
        goals_text = ""
        if goals_path.exists():
            goals = json.loads(goals_path.read_text(encoding="utf-8"))
            active = [g for g in goals if g.get("status") == "active"]
            goals_text = f"{len(active)} active goals"

        state = _load_state()
        save_handoff_note(
            summary=f"Auto-checkpoint #{state.get('checkpoints_run', 0) + 1}: "
            f"{state.get('edits', 0)} edits, {state.get('tool_calls', 0)} tool calls",
            goals_state=goals_text,
            context_snapshot={
                "type": "checkpoint",
                "edits": state.get("edits", 0),
                "tool_calls": state.get("tool_calls", 0),
                "timestamp": time.time(),
            },
        )
        parts.append("handoff note updated")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: handoff note failed: %s", e)

    # 3. Log checkpoint event to ledger
    try:
        state = _load_state()
        emit_event(
            "SESSION_CHECKPOINT",
            {
                "edits": state.get("edits", 0),
                "tool_calls": state.get("tool_calls", 0),
                "checkpoints_run": state.get("checkpoints_run", 0) + 1,
            },
            actor="system",
            validate=False,
        )
        parts.append("ledger checkpoint logged")
    except (OSError, ValueError, KeyError) as e:
        logger.warning("Checkpoint: ledger event failed: %s", e)

    # 4. Update counter state
    state = _load_state()
    state["checkpoints_run"] = state.get("checkpoints_run", 0) + 1
    state["last_checkpoint"] = time.time()
    _save_state(state)

    return "Checkpoint: " + ", ".join(parts) if parts else "Checkpoint: nothing saved"


# ─── Self-Awareness Practice Monitor ─────────────────────────────────

# If no affect log, compass observation, or decision in this many tool calls,
# surface a gentle nudge. Not a gate — just awareness.
PRACTICE_NUDGE_THRESHOLD = 100


def check_self_awareness_practice(tool_calls: int | None = None) -> str | None:
    """Check whether self-awareness tools have been used this session.

    Returns a nudge string if practice has lapsed, or None if all clear.
    DivineOS monitors substrate health periodically — this monitors
    self-awareness practice health with the same approach.
    """
    if tool_calls is None:
        state = _load_state()
        tool_calls = state.get("tool_calls", 0)

    if tool_calls < PRACTICE_NUDGE_THRESHOLD:
        return None  # Too early to nudge

    session_start = get_session_start_time()
    if session_start is None:
        return None

    # Check for recent self-awareness activity since session start
    missing: list[str] = []
    try:
        from divineos.core.memory import _get_connection

        conn = _get_connection()
        try:
            # Affect: any entries since session start?
            try:
                affect_row = conn.execute(
                    "SELECT COUNT(*) FROM affect_log WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if affect_row and affect_row[0] == 0:
                    missing.append("affect (divineos feel)")
            except Exception:  # noqa: BLE001
                pass

            # Compass: any observations since session start?
            try:
                compass_row = conn.execute(
                    "SELECT COUNT(*) FROM compass_observation WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if compass_row and compass_row[0] == 0:
                    missing.append("compass (divineos compass-ops observe)")
            except Exception:  # noqa: BLE001
                pass

            # Decisions: any entries since session start?
            try:
                decision_row = conn.execute(
                    "SELECT COUNT(*) FROM decision_journal WHERE created_at > ?",
                    (session_start,),
                ).fetchone()
                if decision_row and decision_row[0] == 0:
                    missing.append("decisions (divineos decide)")
            except Exception:  # noqa: BLE001
                pass
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        return None  # Don't nudge if DB is unavailable

    if not missing:
        return None

    return (
        f"Self-awareness check: {tool_calls} tool calls, "
        f"no {', '.join(missing)} logged this session. "
        "Consider checking in with yourself."
    )
