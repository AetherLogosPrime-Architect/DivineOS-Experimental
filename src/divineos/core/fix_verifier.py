"""Fix verifier — catches premature "it's fixed" claims.

Lesson x4 (active): "I claimed something was fixed but the error came back."

## Architecture

After a tool failure followed by an Edit (likely a fix attempt), the
system sets a "pending verification" marker. If the agent then tries
another Edit or Write (moving on to new work) without running tests
or re-running the failed command, it gets an advisory nudge.

This is advisory (soft-advise), not blocking. The agent might be making
a multi-file fix that requires several edits before verification.
Blocking would be too aggressive.

## How it works

1. PostToolUse records failures in the retry_tracker (shared with retry_blocker).
2. PostToolUse detects when an Edit follows a failure (fix attempt).
3. Sets a "pending_verification" marker.
4. PreToolUse checks: if pending_verification is set and the next tool
   is Edit/Write (new work without verification), emit advisory.
5. Running tests (pytest, Bash with test commands) or re-running the
   failed command clears the marker.

## Marker file

``~/.divineos/pending_verification.json`` — simple JSON with the
fix details. Auto-expires after 10 minutes.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from divineos.core.paths import marker_path as _marker_path

VERIFICATION_EXPIRY_SECONDS = 600  # 10 minutes


def _marker_file() -> Path:
    return _marker_path("pending_verification.json")


def mark_fix_attempted(file_path: str, error_context: str = "") -> None:
    """Record that a fix was attempted — verification is now expected."""
    path = _marker_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": time.time(),
        "file_path": file_path,
        "error_context": error_context[:200],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def clear_verification() -> None:
    """Clear the pending verification marker (tests ran or command re-run)."""
    path = _marker_file()
    if path.exists():
        path.unlink(missing_ok=True)


def check_verification_needed(tool_name: str) -> str | None:
    """Check if the agent is moving on without verifying a fix.

    Returns advisory message if pending, None otherwise.
    """
    if tool_name not in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return None

    path = _marker_file()
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    ts = data.get("timestamp", 0)
    if time.time() - ts > VERIFICATION_EXPIRY_SECONDS:
        path.unlink(missing_ok=True)
        return None

    file_name = Path(data.get("file_path", "")).name
    age = int(time.time() - ts)

    return (
        f"VERIFY-FIX REMINDER: You edited {file_name} {age}s ago as a fix, "
        f"but haven't verified it works yet. Run tests or re-run the "
        f"failed command before moving on. "
        f"(Lesson x4: 'claimed fixed but the error came back.')"
    )


def is_verification_command(tool_name: str, tool_input: dict[str, Any]) -> bool:
    """True if this tool call counts as fix verification."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        verification_prefixes = (
            "pytest",
            "python -m pytest",
            "python -m unittest",
            "npm test",
            "cargo test",
            "go test",
            "make test",
            "bash scripts/precommit",
        )
        for prefix in verification_prefixes:
            if cmd.startswith(prefix):
                return True
        # Re-running the same kind of command that failed
        # is also verification (checking if the fix worked)
    return False
