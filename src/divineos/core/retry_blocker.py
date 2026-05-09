"""Retry blocker — prevents blind retries without diagnostic investigation.

Lesson x11 (most repeated behavioral failure): "I retried a failed
action without investigating the cause." This module is the riverbank.

## Architecture (Revelation principle)

Make the right path cheap: diagnostic commands (Read, Grep, git diff,
divineos ask) automatically clear the block. Make the wrong path
expensive: retrying a failed command without investigation is blocked.

## How it works

1. PostToolUse hook calls ``record_failure()`` when a tool errors.
2. PreToolUse gate calls ``check_retry()`` on the next tool call.
3. If the upcoming command has the same signature as a recent
   uninvestigated failure, the gate blocks.
4. Any diagnostic command calls ``mark_investigated()``, clearing
   the block.

## Marker file

``~/.divineos/retry_tracker.json`` — a list of recent failure records.
Auto-expires after 5 minutes. Ring buffer capped at 10 entries.

## Calibration (over-inclusive principle)

Wide net on "same command" (tool_name + target file or first 3 words).
Narrow gate on what clears (only genuine read/inspect commands count).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from divineos.core.paths import marker_path as _marker_path_under_home

FAILURE_EXPIRY_SECONDS = 300
MAX_TRACKED_FAILURES = 10

_DIVINEOS_SUBCMD_RE = re.compile(r"\bdivineos\s+(\w[\w-]*)")


def _tracker_path() -> Path:
    return _marker_path_under_home("retry_tracker.json")


def _load_tracker() -> list[dict[str, Any]]:
    path = _tracker_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
    except (json.JSONDecodeError, OSError):
        return []
    now = time.time()
    return [e for e in data if now - e.get("timestamp", 0) < FAILURE_EXPIRY_SECONDS]


def _save_tracker(entries: list[dict[str, Any]]) -> None:
    path = _tracker_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries[-MAX_TRACKED_FAILURES:]), encoding="utf-8")


def _command_signature(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Extract a similarity signature for retry detection.

    Two calls are "substantially similar" if they produce the same
    signature. Over-inclusive by design — false positives are cheap
    (agent just has to read something first), false negatives are
    expensive (blind retry loop continues).
    """
    if tool_name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return f"{tool_name}:{tool_input.get('file_path', '')}"
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        parts = cmd.split()[:3]
        return f"Bash:{' '.join(parts)}"
    # For other tools, use tool name + first string argument
    for _k, v in sorted(tool_input.items()):
        if isinstance(v, str) and v:
            return f"{tool_name}:{v[:60]}"
    return tool_name


def record_failure(tool_name: str, tool_input: dict[str, Any], error: str = "") -> None:
    """Record a tool failure. Called by PostToolUse on error."""
    entries = _load_tracker()
    entries.append(
        {
            "timestamp": time.time(),
            "signature": _command_signature(tool_name, tool_input),
            "tool_name": tool_name,
            "error_snippet": error[:200],
            "investigated": False,
        }
    )
    _save_tracker(entries)


def mark_investigated() -> None:
    """Mark all failures as investigated. Called when a diagnostic runs."""
    entries = _load_tracker()
    if not entries:
        return
    for e in entries:
        e["investigated"] = True
    _save_tracker(entries)


def clear_all() -> None:
    """Remove the tracker file entirely."""
    path = _tracker_path()
    if path.exists():
        path.unlink(missing_ok=True)


def check_retry(tool_name: str, tool_input: dict[str, Any]) -> str | None:
    """Check if this tool call is a blind retry of a recent failure.

    Returns denial message string if blocking, None if allowed.
    """
    entries = _load_tracker()
    if not entries:
        return None

    sig = _command_signature(tool_name, tool_input)
    matches = [e for e in entries if e.get("signature") == sig and not e.get("investigated", False)]
    if not matches:
        return None

    last = matches[-1]
    err = last.get("error_snippet", "")
    age = int(time.time() - last.get("timestamp", 0))

    return (
        f"BLOCKED: This looks like a retry of a command that failed {age}s ago "
        f"without investigation in between. "
        f"{'Error was: ' + err + '. ' if err else ''}"
        f"Investigate first — read the error, check the file, understand why "
        f"it failed. Diagnostic commands (Read, Grep, Glob, git diff/log/status, "
        f"divineos ask/recall/context) clear this block automatically."
    )


# --- Diagnostic detection ---

_DIAGNOSTIC_TOOLS = frozenset({"Read", "Grep", "Glob"})

_DIAGNOSTIC_BASH_PREFIXES = (
    "git log",
    "git diff",
    "git status",
    "git show",
    "cat ",
    "head ",
    "tail ",
    "ls ",
    "find ",
    "python -c",
    "type ",
)

_DIAGNOSTIC_DIVINEOS = frozenset(
    {
        "ask",
        "recall",
        "context",
        "briefing",
        "inspect",
        "body",
        "health",
        "verify",
    }
)


def is_diagnostic_command(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """True if this tool call counts as diagnostic investigation."""
    if tool_name in _DIAGNOSTIC_TOOLS:
        return True
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        for prefix in _DIAGNOSTIC_BASH_PREFIXES:
            if cmd.startswith(prefix):
                return True
        m = _DIVINEOS_SUBCMD_RE.search(cmd)
        if m and m.group(1) in _DIAGNOSTIC_DIVINEOS:
            return True
    return False
