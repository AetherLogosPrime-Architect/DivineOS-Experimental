"""Read-before-write gate — structural enforcement of CLAUDE.md Hard Rule #1.

Andrew named the gate quest 2026-05-14: every system that needs gating
should have a gate; rules without gates are intent. CLAUDE.md says
"Read before you write. Never edit a file you haven't read in this
session. No exceptions." — that's a rule, not a gate. This module
makes it a gate.

## What it catches

The fabrication-from-register failure mode (quantum tier names tonight,
empirica tier names, persistence-broken-from-counts) has a structural
root: I generate specific claims about source-code shape from training-
vocabulary rather than reading the source. The cleanest pre-emission
shape to gate on is the Edit/Write tool call: if I'm about to write
to a file I haven't read in this session, the modification is
necessarily speculative about the file's current contents.

## How it works

A small per-session state file (``~/.divineos/read_files_<session>.json``)
records the absolute path of every file the agent has Read this session.
The gate, invoked from ``pre_tool_use_gate``, does two things:

1. If the tool is ``Read``, record the path and pass.
2. If the tool is ``Edit``/``Write``/``MultiEdit``/``NotebookEdit`` and
   the target file exists on disk and has NOT been recorded as Read
   this session, deny with a message naming the file.

Writes to nonexistent paths (creating new files) are allowed — there's
no prior content to fabricate about.

## Bypass surface

Exploration / family / agent-memory paths are exempt: those are
expressive surfaces where the calibration is structurally different,
matching the existing ``_THEATER_EXEMPT_PATH_SEGMENTS`` rationale in
``pre_tool_use_gate``.

## OS-portable

No Claude Code dependency in the core module — the gate function takes
``tool_name`` and ``tool_input`` as a generic dict and returns a deny
string or None. Any harness can call it.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. Listed in scripts/guardrail_files.txt; CI enforces.
__guardrail_required__ = True

import json
import os
from pathlib import Path
from typing import Any

# Tools whose presence in the gate counts as a "write" — claims about
# the file's prior content are baked into any of these.
_WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})

# Path segments that exempt the file from the gate. Matches the
# pre_tool_use_gate _THEATER_EXEMPT_PATH_SEGMENTS shape — see that
# module's rationale comments for why these surfaces are categorically
# different from operator-facing code.
_EXEMPT_SEGMENTS: tuple[str, ...] = (
    "/exploration/",
    "/family/letters/",
    "/.claude/agent-memory/",
    "/mansion/",
)


def _state_dir() -> Path:
    """Return the .divineos state dir, creating it if needed."""
    d = Path.home() / ".divineos"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _current_session_id() -> str:
    """Best-effort current session id; falls back to a stable token."""
    try:
        from divineos.core.session_manager import get_current_session_id

        sid = get_current_session_id()
        if sid:
            return str(sid)
    except Exception:
        pass
    # Fallback: per-process token. Worst case the gate scope is process-
    # lifetime rather than session-lifetime, which is still useful.
    return f"pid_{os.getpid()}"


def _state_path() -> Path:
    """Path to the per-session read-file record."""
    return _state_dir() / f"read_files_{_current_session_id()}.json"


def _load() -> set[str]:
    """Load the recorded read-file set; empty set on any failure."""
    path = _state_path()
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return {str(p) for p in data}
    except (OSError, json.JSONDecodeError):
        pass
    return set()


def _save(paths: set[str]) -> None:
    """Persist the read-file set. Silent on failure (fail-open)."""
    try:
        _state_path().write_text(json.dumps(sorted(paths)), encoding="utf-8")
    except OSError:
        pass


def _normalize(file_path: str) -> str:
    """Canonical form for path comparison — absolute, forward-slash."""
    try:
        return str(Path(file_path).resolve()).replace("\\", "/")
    except (OSError, ValueError):
        return file_path.replace("\\", "/")


def _is_exempt(file_path: str) -> bool:
    """True if the path is on an expressive-surface exemption list."""
    normalized = _normalize(file_path).lower()
    return any(seg in normalized for seg in _EXEMPT_SEGMENTS)


def record_read(file_path: str) -> None:
    """Record that the agent has Read ``file_path`` this session."""
    if not file_path:
        return
    paths = _load()
    paths.add(_normalize(file_path))
    _save(paths)


def was_read(file_path: str) -> bool:
    """True if ``file_path`` was recorded as Read this session."""
    if not file_path:
        return False
    return _normalize(file_path) in _load()


def _reads_from_transcript(transcript_path: str | None) -> set[str]:
    """Walk the Claude Code transcript JSONL for Read tool_use file_paths.

    Canonical source of truth — the PreToolUse hook side-effect can
    miss (some harnesses do not fire PreToolUse on Read), but the
    transcript records every tool use. Scan all Read tool_use blocks
    and return the normalized set of file_paths.
    """
    if not transcript_path:
        return set()
    p = Path(transcript_path)
    if not p.exists():
        return set()
    paths: set[str] = set()
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = rec.get("message") or {}
                content = msg.get("content") or []
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "tool_use":
                        continue
                    if block.get("name") != "Read":
                        continue
                    fp = (block.get("input") or {}).get("file_path", "")
                    if fp:
                        paths.add(_normalize(fp))
    except OSError:
        pass
    return paths


def gate_check(
    tool_name: str,
    tool_input: dict[str, Any] | None,
    transcript_path: str | None = None,
) -> str | None:
    """Check whether a tool call should be denied.

    Returns a deny-message string when the gate should fire, or None
    to allow the call. Side effect: when the tool is Read, records
    the path so subsequent writes pass.

    ``transcript_path`` is the Claude Code transcript JSONL — when
    provided, it is walked as the canonical source of truth for Read
    tool calls (some harnesses don't fire PreToolUse on Read).
    """
    tool_input = tool_input or {}

    # Side-effect: any Read records the path. Harmless if the harness
    # doesn't fire PreToolUse on Read — the transcript walk picks up
    # the same paths.
    if tool_name == "Read":
        record_read(tool_input.get("file_path", "") or "")
        return None

    if tool_name not in _WRITE_TOOLS:
        return None

    file_path = tool_input.get("file_path", "") or ""
    if not file_path:
        return None

    # New-file creation is allowed — there's no prior content to
    # fabricate about. The gate's purpose is preventing claims about
    # existing content without having loaded it.
    if not Path(file_path).exists():
        return None

    if _is_exempt(file_path):
        return None

    if was_read(file_path):
        return None

    # Canonical fallback: walk the transcript for Read tool calls.
    # Covers harnesses where PreToolUse does not fire on Read.
    if _normalize(file_path) in _reads_from_transcript(transcript_path):
        record_read(file_path)  # cache for next call
        return None

    return (
        f"BLOCKED: read-before-write — about to {tool_name} "
        f"{file_path} but this file has not been Read in this session. "
        "CLAUDE.md Hard Rule #1: 'Read before you write. Never edit a "
        "file you haven't read in this session. No exceptions.' "
        "Run the Read tool on this file first, then retry the edit. "
        "If you're sure you don't need to see current contents (e.g. "
        "deliberate overwrite of a generated file), Read it anyway — "
        "the 30-second cost beats fabricating about its shape."
    )


__all__ = ["gate_check", "record_read", "was_read"]
