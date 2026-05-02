"""Consolidated PostToolUse checkpoint — single Python invocation for all tracking.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/session-checkpoint.sh as
# ``python -m divineos.hooks.post_tool_use_checkpoint``. This module
# collapses the 8+ separate Python invocations the old
# session-checkpoint.sh was making into a single interpreter run.

## Why this exists

The previous session-checkpoint.sh made many sequential Python calls:
reading state, writing state, recording tool use, recording code
actions, saving updated state, checking self-awareness practice,
context monitoring. On Windows each spawn costs ~200ms of startup
plus DivineOS import. Total was ~600ms per PostToolUse firing, and
this hook fires on every Edit / Write / Bash.

This module does all the same work in one interpreter invocation.
Expected improvement: ~4x faster (600ms → ~150ms) which compounds
across every tool call.

## What it does (same as old shells, consolidated)

1. Read hook input (tool_name, tool_input)
2. Load checkpoint state from ``~/.divineos/checkpoint_state.json``
3. Increment tool_calls counter; increment edits if Edit/Write
4. Record tool use for lesson-interrupt pattern detection
5. Record code action for periodic engagement gate (Edit/Write only)
6. Save updated state
7. If edits crossed a 15-multiple threshold, run ``divineos checkpoint``
8. Emit context-monitor warnings at 100 / 150 tool-call thresholds
9. Emit self-awareness practice nudge if tool_calls >= 100
10. **Lesson-interrupt check** (Edit/Write/NotebookEdit only): run
    ``check_lesson_interrupt`` and surface any question that fires
11. **Pattern anticipation** (Edit/Write only, throttled every 5 edits):
    run ``anticipate`` on the file-path context and surface warnings
12. Output combined ``additionalContext`` JSON for Claude Code if any
    warnings / nudges / interrupts accumulated

All twelve operations in one Python process. Fail-open design — if any
individual step errors, the hook keeps running; the OS never gets
bricked by the hook.

## P3 consolidation (2026-04-19)

Originally three shell hooks fired on Edit/Write/Bash/NotebookEdit:
session-checkpoint (~260ms), pattern-anticipation (~280ms),
lesson-interrupt (~150ms). Total ~690ms per Edit/Write. P3 folded
anticipation and lesson-interrupt into this module. Expected savings:
~430ms per Edit/Write (two fewer process spawns, imports shared across
the consolidated work).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_CHECKPOINT_EDIT_INTERVAL = 15
_CONTEXT_WARNING_THRESHOLD = 100
_AUTO_SESSION_END_THRESHOLD = 150

# Pattern-anticipation runs on every Nth edit to avoid noise. Matches
# the throttle the old pattern-anticipation.sh implemented.
_ANTICIPATION_THROTTLE = 5

# Keys used in the checkpoint state dict for anticipation tracking.
# Separate from the main edit counter so anticipation and checkpoint
# don't share throttle boundaries.
_ANTICIPATION_COUNTER_KEY = "anticipation_edit_count"


def _state_path() -> Path:
    """Path to the checkpoint state JSON. Uses expanduser for Windows."""
    divineos_dir = Path(os.path.expanduser("~")) / ".divineos"
    divineos_dir.mkdir(exist_ok=True)
    return divineos_dir / "checkpoint_state.json"


def _auto_emitted_path() -> Path:
    """Path to the auto-emit marker file."""
    divineos_dir = Path(os.path.expanduser("~")) / ".divineos"
    return divineos_dir / "auto_session_end_emitted"


def _load_state() -> dict[str, Any]:
    """Load checkpoint state, creating defaults if missing."""
    path = _state_path()
    if not path.exists():
        return {"edits": 0, "tool_calls": 0, "last_checkpoint": 0, "checkpoints_run": 0}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, json.JSONDecodeError):
        return {"edits": 0, "tool_calls": 0, "last_checkpoint": 0, "checkpoints_run": 0}


def _save_state(state: dict[str, Any]) -> None:
    """Write checkpoint state. Silent on error."""
    try:
        _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def _record_tool_for_interrupt(tool_name: str, file_path: str) -> None:
    """Record tool use for lesson-interrupt pattern detection."""
    try:
        from divineos.core.lesson_interrupt import record_tool_for_interrupt

        record_tool_for_interrupt(tool_name, file_path)
    except (ImportError, OSError, AttributeError):
        pass


def _record_code_action() -> None:
    """Record a code action for the periodic engagement gate."""
    try:
        from divineos.core.hud_handoff import record_code_action

        record_code_action()
    except (ImportError, OSError, AttributeError):
        pass


def _check_self_awareness_practice(tool_calls: int) -> str:
    """Check whether a self-awareness practice nudge should fire."""
    if tool_calls < _CONTEXT_WARNING_THRESHOLD:
        return ""
    try:
        from divineos.core.session_checkpoint import check_self_awareness_practice

        result = check_self_awareness_practice(tool_calls)
        return result or ""
    except (ImportError, OSError, AttributeError):
        return ""


def _fire_and_forget(cmd: list[str], env: dict[str, str] | None = None) -> None:
    """Spawn ``cmd`` as a detached background subprocess and return immediately.

    The PostToolUse hook used to block on ``divineos extract`` and
    ``divineos checkpoint`` synchronously. Extract runs the full
    consolidation pipeline (~30–60s) which means every time the
    write-threshold is crossed the user waits that long before their
    next tool call completes. That's the main source of felt "slow
    replies" in long sessions.

    This helper spawns the command in the background so the hook
    returns in ~100ms instead of tens of seconds. The subprocess
    continues independently.

    Subprocess stderr is captured to a per-invocation log file under
    ``~/.divineos/failures/extract_stderr/<timestamp>.log`` rather than
    DEVNULL. This addresses fresh-Claude audit round 2 Finding 4
    (silent failure surface): previously, a subprocess crash mid-extract
    was invisible because stderr went to DEVNULL and the marker was
    already set. Now the stderr file exists on disk and the next
    briefing's extract-diagnostic surface can read it.

    Windows and Unix behaviors diverge slightly. Using CREATE_NO_WINDOW
    on Windows to suppress a terminal flash.
    """
    try:
        # Per-invocation stderr log — preserves the detach-immediately
        # semantics while making subprocess failures visible on disk.
        stderr_log = _open_stderr_log_for_cmd(cmd)

        kwargs: dict = {
            "stdout": subprocess.DEVNULL,
            "stderr": stderr_log or subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
        }
        if env is not None:
            kwargs["env"] = env
        # On Windows, avoid flashing a console window for the background subprocess.
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            # On Unix, start a new session so the subprocess survives the hook.
            kwargs["start_new_session"] = True

        # Record that an invocation was started, with stderr path reference,
        # so diagnostics can correlate a failure file back to the intent.
        try:
            from divineos.core.failure_diagnostics import record_failure

            record_failure(
                "extract_launch",
                {
                    "cmd": " ".join(cmd),
                    "stderr_log": str(stderr_log.name) if stderr_log else None,
                },
            )
        except Exception:  # noqa: BLE001 — diagnostic best-effort
            pass

        subprocess.Popen(cmd, **kwargs)
    except (OSError, subprocess.SubprocessError):
        pass


def _open_stderr_log_for_cmd(cmd: list[str]):
    """Open a per-invocation stderr log file under ~/.divineos/failures/.

    Returns an open file handle the subprocess can write to, or None on
    error. Rotates old logs — keeps at most the 20 most recent files so
    the directory doesn't grow unboundedly over long sessions.
    """
    try:
        log_dir = Path.home() / ".divineos" / "failures" / "extract_stderr"
        log_dir.mkdir(parents=True, exist_ok=True)
        _rotate_stderr_logs(log_dir, keep=20)
        cmd_tag = "".join(c for c in (cmd[1] if len(cmd) > 1 else "cmd") if c.isalnum())
        path = log_dir / f"{int(time.time())}_{cmd_tag}.log"
        return path.open("w", encoding="utf-8")
    except OSError:
        return None


def _rotate_stderr_logs(log_dir: Path, keep: int = 20) -> None:
    """Keep at most ``keep`` most-recent .log files in log_dir; delete the rest."""
    try:
        files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
    except OSError:
        return
    if len(files) <= keep:
        return
    for old in files[:-keep]:
        try:
            old.unlink()
        except OSError:
            continue


def _run_checkpoint() -> None:
    """Fire ``divineos checkpoint`` in the background.

    Previously blocked up to 30s; now returns in ~100ms. Checkpoint is
    a bookkeeping operation — if it gets killed when the session ends,
    no data is lost (the state it updates is reconstructed at
    SessionStart anyway).
    """
    _fire_and_forget(["divineos", "checkpoint"])


def _auto_run_extract() -> None:
    """Fire ``divineos extract`` in the background; mark so we don't repeat.

    Previously blocked up to 60s inside the PostToolUse hook — the
    dominant source of felt latency on writes. Now fire-and-forget.

    The marker file prevents repeated triggering. We write the marker
    BEFORE firing the subprocess, not after, because we're not waiting
    for completion. If the subprocess fails partway through, re-running
    it mid-session would be worse than letting the next SessionStart
    handle the residual — so we commit to "extract was triggered" as
    soon as we trigger it.
    """
    marker = _auto_emitted_path()
    if marker.exists():
        return
    # Pre-mark to avoid repeated firing if the hook runs again before
    # the background subprocess completes. Uses the same trigger-attributed
    # format as the normal extract path (see core/extract_marker.py).
    try:
        from divineos.core.extract_marker import write_marker

        write_marker(trigger="hook-async")
    except (ImportError, OSError, AttributeError):
        # Fall back to legacy literal marker so at least idempotency holds.
        try:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text("1", encoding="utf-8")
        except OSError:
            pass
    env = os.environ.copy()
    env["DIVINEOS_EXTRACT_TRIGGER"] = "hook"
    _fire_and_forget(["divineos", "extract"], env=env)


def _get_writes_since_consolidation() -> int:
    """Read the writes_since_consolidation counter. Returns 0 on any error
    (best-effort; we don't want counter-read failures to block the hook)."""
    try:
        from divineos.core.session_checkpoint import _load_state

        state = _load_state()
        return int(state.get("writes_since_consolidation", 0))
    except (ImportError, OSError, ValueError, TypeError):
        return 0


def _get_write_threshold() -> int:
    """Read the consolidation write threshold constant. Defaults to 40 if
    import fails (bootstrap path)."""
    try:
        from divineos.core.session_checkpoint import CONSOLIDATION_WRITE_THRESHOLD

        return int(CONSOLIDATION_WRITE_THRESHOLD)
    except (ImportError, ValueError, TypeError):
        return 40


def _check_lesson_interrupt(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Run the mid-session lesson-interrupt check. Returns question string
    or empty. Only fires for Edit/Write/NotebookEdit — other tool types
    skip the check (interrupts are tied to code-modifying work)."""
    if tool_name not in ("Edit", "Write", "NotebookEdit"):
        return ""
    try:
        from divineos.core.lesson_interrupt import check_lesson_interrupt

        result = check_lesson_interrupt(tool_input or {})
        return result or ""
    except (ImportError, OSError, AttributeError):
        return ""


def _run_anticipation(tool_name: str, file_path: str, state: dict[str, Any]) -> str:
    """Run pattern-anticipation on file-edit context. Throttled to every
    Nth edit (_ANTICIPATION_THROTTLE) to avoid repeat noise. Returns
    formatted warnings or empty.

    Throttle state lives in the checkpoint state dict under
    _ANTICIPATION_COUNTER_KEY — carried over from the old
    anticipation_state.json file, now part of the unified state.
    """
    if tool_name not in ("Edit", "Write"):
        return ""
    if not file_path:
        return ""

    count = int(state.get(_ANTICIPATION_COUNTER_KEY, 0)) + 1
    state[_ANTICIPATION_COUNTER_KEY] = count
    if count % _ANTICIPATION_THROTTLE != 0:
        return ""

    try:
        from divineos.core.anticipation import anticipate, format_anticipation

        warnings = anticipate(f"Editing: {file_path}", max_warnings=3)
        if not warnings:
            return ""
        return format_anticipation(warnings) or ""
    except (ImportError, OSError, AttributeError):
        return ""


def main() -> int:
    """Entry point. Reads hook input, runs all checkpoint operations, emits
    optional additionalContext for Claude Code."""
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        input_data = {}

    tool_name = ""
    tool_input: dict[str, Any] = {}
    try:
        tool_name = input_data.get("tool_name", "") or ""
        tool_input = input_data.get("tool_input", {}) or {}
    except (AttributeError, TypeError):
        pass

    file_path = ""
    try:
        file_path = tool_input.get("file_path", tool_input.get("command", "")) or ""
    except (AttributeError, TypeError):
        pass

    state = _load_state()
    state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
    if tool_name in ("Edit", "Write"):
        state["edits"] = int(state.get("edits", 0)) + 1

    # Track tool use for lesson-interrupt pattern detection
    if tool_name in ("Read", "Edit", "Write", "Bash"):
        _record_tool_for_interrupt(tool_name, file_path)

    # Code action → engagement gate tracking (writes only)
    if tool_name in ("Edit", "Write", "NotebookEdit"):
        _record_code_action()

    tool_calls = state["tool_calls"]
    edits = state["edits"]
    checkpoints_run = int(state.get("checkpoints_run", 0))

    # Check if periodic checkpoint needed (every 15 edits)
    edits_since = edits - (checkpoints_run * _CHECKPOINT_EDIT_INTERVAL)
    if edits_since >= _CHECKPOINT_EDIT_INTERVAL:
        _run_checkpoint()
        state["checkpoints_run"] = checkpoints_run + 1
        state["last_checkpoint"] = time.time()

    # Pattern anticipation — throttled to every Nth Edit/Write. Runs on the
    # mutated state (so the counter is part of the checkpoint_state).
    anticipation_msg = _run_anticipation(tool_name, file_path, state)

    # Save state (includes the anticipation counter update)
    _save_state(state)

    # Build any warnings / nudges / interrupts
    messages: list[str] = []

    # Lesson-interrupt check fires for every code-modifying tool use.
    # This was previously a separate hook that ran ~150ms per call;
    # folded in here it's effectively free because the imports are
    # already warm.
    interrupt = _check_lesson_interrupt(tool_name, tool_input)
    if interrupt:
        messages.append(interrupt)

    if anticipation_msg:
        messages.append(anticipation_msg)

    practice = _check_self_awareness_practice(tool_calls)
    if practice:
        messages.append(practice)

    # Write-count trigger (PR #2). Fires when accumulated writes since last
    # consolidation cross the threshold. Writes = meaningful-work ledger
    # events (corrections, decisions, opinions, knowledge stores). Not
    # every tool call — just the ones that produced something worth
    # consolidating. See CONSOLIDATION_WRITE_THRESHOLD in session_checkpoint.
    writes_since = _get_writes_since_consolidation()
    write_threshold = _get_write_threshold()

    if writes_since >= write_threshold:
        _auto_run_extract()
        messages.append(
            f"Consolidation auto-run: {writes_since} writes accumulated "
            f"since last checkpoint. Knowledge saved; extraction pipeline ran."
        )
    elif tool_calls >= _AUTO_SESSION_END_THRESHOLD:
        # Fallback: tool-call threshold (legacy context-pressure proxy).
        # Stays as a safety net in case write-count misses something.
        _auto_run_extract()
        messages.append(
            f"Consolidation auto-run at {tool_calls} tool calls "
            "(tool-call fallback). Knowledge saved."
        )
    elif tool_calls >= _CONTEXT_WARNING_THRESHOLD:
        messages.append(
            f"Context monitor: {tool_calls} tool calls, {edits} edits, "
            f"{writes_since}/{write_threshold} writes toward next consolidation."
        )

    if messages:
        payload = {"additionalContext": " | ".join(messages)}
        json.dump(payload, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
