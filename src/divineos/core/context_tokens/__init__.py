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

SECOND FOSSIL (Andrew 2026-08-18, correction #452):
An honest read of the WRONG session is not an honest gauge. This
module used to locate the transcript by mapping the shell's current
working directory to a project folder and taking the newest file in
it by mtime. Run `divineos context-tokens` after `cd`-ing anywhere
other than the window's own worktree and it answered about a stranger.
On 2026-08-18 it reported 961,358 tokens (96.1%) while the live session
held 439,200 (44%). The number was real, the arithmetic was right, and
it came from a 67MB abandoned session whose last usage block was
stamped 2026-06-10 — sixty-nine days dead, its mtime freshened by
something that never wrote a usage record.

Worse: that exact bug, in that exact abandoned transcript, was found
and fixed on 2026-06-10 (Andrew correction #50) — in
`scripts/compaction_token_monitor.py` (retired 2026-08-22 with the
delivery cluster; this resolver outlived its only caller). One of two
copies was repaired; the other kept lying for sixty-nine days. So the
resolver lives here now, once, and the monitor imports it.

Resolution is pinned to the launching session's id
(``CLAUDE_CODE_SESSION_ID``), because a process asking "how full am I?"
has to be answered about ITSELF. Where no session id exists the mtime
fallback still runs so other harnesses keep working — but the snapshot
comes back ``pinned=False``, and any caller about to spend the number
on a decision must refuse an unpinned one.
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
    pinned: bool = False
    """True when the transcript was resolved by session id.

    False means the reading came from the mtime fallback and may belong
    to another session entirely. An unpinned reading is fine to display
    and must not be spent on a decision.
    """


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


def _session_id_from_env() -> str | None:
    """The launching session's uuid, if the harness published one."""
    return os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CLAUDE_SESSION_ID")


def find_active_transcript(
    cwd: str | None = None,
    projects_dir: Path | None = None,
    session_id: str | None = None,
) -> tuple[Path | None, bool]:
    """Resolve the asking session's transcript file.

    Returns ``(path, pinned)``. ``pinned`` is True only when the file was
    found by session id — the one resolution that cannot quietly answer
    about somebody else.

    Order:
      1. ``<session_id>.jsonl`` anywhere under the projects dir. A session
         can be launched from a different directory than the shell
         currently sits in, so this searches every project folder rather
         than guessing the folder from the cwd.
      2. Newest mtime inside the cwd-derived project folder.
      3. Newest mtime across all project folders.

    Steps 2 and 3 return ``pinned=False``. They exist so a harness with no
    ``CLAUDE_CODE_SESSION_ID`` still gets a reading — not so the reading
    can be trusted with a decision.

    Parameters are injectable for tests; at runtime they resolve from
    ``Path.home()``, ``os.getcwd()`` and the env vars. Passing them
    directly keeps tests off the real ``~/.claude/projects/`` and away
    from env-var state leaked between tests in a shared pytest session.
    """
    if projects_dir is None:
        projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.is_dir():
        return None, False

    if session_id is None:
        session_id = _session_id_from_env()
    if session_id:
        matches = list(projects_dir.rglob(f"{session_id}.jsonl"))
        if matches:
            return max(matches, key=lambda p: p.stat().st_mtime), True
        # Env var set but the transcript is not on disk yet (first turn of
        # a session). Fall through so the caller still gets a number.

    own_dir = projects_dir / _encode_cwd_for_claude(cwd)
    if own_dir.is_dir():
        local = list(own_dir.glob("*.jsonl"))
        if local:
            return max(local, key=lambda p: p.stat().st_mtime), False

    candidates = list(projects_dir.rglob("*.jsonl"))
    if not candidates:
        return None, False
    return max(candidates, key=lambda p: p.stat().st_mtime), False


def _find_active_transcript(cwd: str | None = None) -> Path | None:
    """Back-compat shim — path only, pinned-ness discarded.

    Kept because the private name was imported from outside this module.
    New code calls :func:`find_active_transcript` and reads the flag.
    """
    return find_active_transcript(cwd)[0]


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
            usage["_timestamp"] = obj.get("timestamp", "")
            return usage
    return None


def get_context_snapshot(cwd: str | None = None) -> ContextSnapshot:
    """Read the current context-window usage from the active transcript.

    Returns a ContextSnapshot. Fail-open: a broken read never raises.
    Check ``snapshot.pinned`` before spending the number on a decision.
    """
    transcript, pinned = find_active_transcript(cwd)
    if transcript is None:
        return ContextSnapshot(note="no Claude Code transcript dir found for this cwd")

    usage = _read_last_usage(transcript)
    if usage is None:
        return ContextSnapshot(
            transcript_path=str(transcript),
            pinned=pinned,
            note="transcript exists but no usage block found in tail",
        )

    cache_read = int(usage.get("cache_read_input_tokens", 0) or 0)
    cache_creation = int(usage.get("cache_creation_input_tokens", 0) or 0)
    input_t = int(usage.get("input_tokens", 0) or 0)
    output_t = int(usage.get("output_tokens", 0) or 0)
    total = cache_read + cache_creation + input_t
    if pinned:
        note = "ok"
    else:
        stamp = usage.get("_timestamp") or "unknown"
        note = (
            "UNPINNED — no session id available, so this is the newest transcript "
            f"on disk ({transcript.name}, last usage stamped {stamp}), not "
            "necessarily this session. Display only; do not decide on it."
        )
    return ContextSnapshot(
        total_tokens=total,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
        input_tokens=input_t,
        output_tokens_last_turn=output_t,
        session_id=usage.get("_session_id", ""),
        transcript_path=str(transcript),
        pinned=pinned,
        note=note,
    )
