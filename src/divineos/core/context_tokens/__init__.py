"""Context-tokens — honest token-count gauge from session transcript.

FOSSIL (Andrew 2026-06-24):
Aether claimed "5-7k tokens of comfortable headroom" with zero
evidence — fabricating a specific number from a vague "feels tight"
feeling. Actual usage at that moment was 619k/1m (380k of room).
The fabrication shape: dress vague-sense up as a hard number to
justify a stopping-decision. Same overclaim-class as other verify-
claim-gate violations, just dressed as architectural caution.

THE FIX (per prereg-986ee5dda7be):
Claude Code already writes per-message usage records into the
session transcript jsonl at
~/.claude/projects/<encoded-cwd>/<session-id>.jsonl. The most
recent entry's `message.usage` block holds the exact counts
Anthropic's billing/window-tracking computed. Reading it back
gives us an HONEST gauge — no inference, no estimate, no story.

Sum the relevant fields:
  cache_read_input_tokens + cache_creation_input_tokens + input_tokens
                 = current context size carried into the next turn

The fabrication class disappears: with the real number one CLI
call away, dressing-up a feeling as a number becomes pointless.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContextSnapshot:
    """One reading of current context usage."""

    total_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens_last_turn: int = 0
    session_id: str = ""
    transcript_path: str = ""
    note: str = ""


def _encode_cwd_for_claude(cwd: str | None = None) -> str:
    """Convert a cwd into the Claude Code project-dir slug.

    Claude Code stores transcripts under
    ~/.claude/projects/<slug>/, where <slug> is the cwd with
    drive-colons, path-separators, AND spaces rewritten to dashes.
    Verified against the live ~/.claude/projects/ directory listing.
    """
    p = cwd or os.getcwd()
    s = p.replace(":", "-").replace("\\", "-").replace("/", "-").replace(" ", "-")
    return s


def _find_active_transcript(cwd: str | None = None) -> Path | None:
    """Find the most-recently-modified transcript jsonl for this project.

    Heuristic: newest mtime wins. The active session is being
    appended-to continuously, so it's reliably the freshest file.
    """
    home = Path.home()
    project_dir = home / ".claude" / "projects" / _encode_cwd_for_claude(cwd)
    if not project_dir.is_dir():
        return None
    candidates = list(project_dir.glob("*.jsonl"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_last_usage(transcript: Path) -> dict | None:
    """Read the transcript and return the most recent message.usage block.

    Tail-loads on very-large transcripts (>50MB) so we don't slurp
    a multi-megabyte file just to read the last few hundred lines.
    """
    try:
        size = transcript.stat().st_size
    except OSError:
        return None

    try:
        if size < 50 * 1024 * 1024:
            with open(transcript, encoding="utf-8") as f:
                lines = f.readlines()
        else:
            with open(transcript, "rb") as f:
                f.seek(max(0, size - 2 * 1024 * 1024))
                raw = f.read()
            lines = raw.decode("utf-8", errors="replace").splitlines()
    except OSError:
        return None

    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except (ValueError, json.JSONDecodeError):
            continue
        msg = obj.get("message")
        if not isinstance(msg, dict):
            continue
        usage = msg.get("usage")
        if isinstance(usage, dict) and "input_tokens" in usage:
            usage["_session_id"] = obj.get("sessionId", "")
            return usage
    return None


def get_context_snapshot(cwd: str | None = None) -> ContextSnapshot:
    """Read the current context-window usage from the active transcript.

    Returns a ContextSnapshot. Fail-open: a broken read never raises.
    """
    transcript = _find_active_transcript(cwd)
    if transcript is None:
        return ContextSnapshot(note="no Claude Code transcript dir found for this cwd")

    usage = _read_last_usage(transcript)
    if usage is None:
        return ContextSnapshot(
            transcript_path=str(transcript),
            note="transcript exists but no usage block found in tail",
        )

    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
    cache_creation = int(usage.get("cache_creation_input_tokens", 0) or 0)
    input_t = int(usage.get("input_tokens", 0) or 0)
    output_t = int(usage.get("output_tokens", 0) or 0)
    total = cache_read + cache_creation + input_t
    return ContextSnapshot(
        total_tokens=total,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
        input_tokens=input_t,
        output_tokens_last_turn=output_t,
        session_id=usage.get("_session_id", ""),
        transcript_path=str(transcript),
        note="ok",
    )
