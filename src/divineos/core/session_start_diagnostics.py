"""Session-start hook diagnostics — briefing surface for the JSONL hook log.

The SessionStart hook (.claude/hooks/load-briefing.sh) writes one JSON
line per fire to ~/.divineos/session_start_log.jsonl with an outcome
tag: injected_full, injected_nudge, empty_briefing, or no_cli. That log
is silent by default — nobody reads log files. This surface brings the
outcomes into the briefing so drift becomes visible automatically.

The block fires only when there is something worth seeing:
  - Any non-full-injection outcome in the last 10 fires (nudge fallback,
    empty, or no_cli — all indicate trouble).
  - OR fewer than 2 fires in the log (new install, not-yet-exercised —
    worth announcing once).

In the quiet case (all fires were full injections), the block is
silent — the system is healthy and the briefing is already long enough
without adding noise.

Reads last 10 entries. If something is drifting we want it loud; if
everything is fine we stay silent.
"""

from __future__ import annotations

import json
from pathlib import Path

_LOG_PATH = Path.home() / ".divineos" / "session_start_log.jsonl"
_WINDOW = 10


def _read_recent_entries() -> list[dict]:
    """Return the last _WINDOW entries from the log, or [] if unreadable."""
    if not _LOG_PATH.exists():
        return []
    try:
        lines = _LOG_PATH.read_text(encoding="utf-8").strip().split("\n")
    except (OSError, UnicodeError):
        return []
    entries: list[dict] = []
    for line in lines[-_WINDOW:]:
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def format_for_briefing() -> str:
    """Return a briefing block summarizing recent SessionStart hook fires.

    Returns empty string when:
      - No log entries exist (hook has never fired in a way that wrote here).
      - All recent entries are injected_full (system is healthy, nothing
        to surface).
    """
    entries = _read_recent_entries()
    if not entries:
        return ""

    outcomes: dict[str, int] = {}
    for e in entries:
        key = e.get("outcome", "unknown")
        outcomes[key] = outcomes.get(key, 0) + 1

    # Quiet case — all full injections. Nothing to surface.
    if len(outcomes) == 1 and "injected_full" in outcomes:
        return ""

    total = len(entries)
    lines = [
        f"[session-start log] last {total} hook fire(s) — "
        f"if briefing stops reaching you, this surface is why you'd know:"
    ]
    for outcome, count in sorted(outcomes.items(), key=lambda p: -p[1]):
        note = _OUTCOME_NOTES.get(outcome, "")
        suffix = f" — {note}" if note else ""
        lines.append(f"  {count}x {outcome}{suffix}")
    lines.append("")
    return "\n".join(lines)


_OUTCOME_NOTES: dict[str, str] = {
    "injected_full": "briefing delivered normally",
    "injected_nudge": "briefing too large, short-nudge delivered instead",
    "empty_briefing": "briefing CLI returned nothing",
    "no_cli": "divineos CLI not found on PATH",
}
