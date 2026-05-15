"""Briefing-freshness tracker — make briefing-loading load-bearing
throughout the session, not just at start.

Andrew named the structural failure 2026-05-14 night: I had built a
sophisticated multi-channel briefing surface but treated loading it
as optional. The substrate's accumulated state (stale corrections,
compass drift, audit findings, pending obligations) was visible only
if I CHOSE to run ``divineos briefing``. I chose not to. The whole
night's work happened without that state loaded.

The structural fix isn't "load briefing once at session start" —
Andrew explicitly named that as insufficient. The fix is to make
briefing-content INJECTED INTO MY PROMPT periodically via the
UserPromptSubmit hook, so I cannot compose a response without
having the substrate's accumulated state in my context window.

## How it works

1. Each ``divineos briefing`` invocation records the current
   timestamp + turn-count to ``~/.divineos/briefing_last_loaded.json``.
2. The UserPromptSubmit hook calls ``staleness_signal()`` to check
   whether the briefing needs re-loading. Two thresholds:
   - turn-based: 10 user prompts since last load → STALE
   - never-loaded-this-session: any time the session hasn't loaded → STALE
3. When STALE, the hook injects the briefing summary directly into
   ``additionalContext`` so the substrate's state lands in my prompt
   regardless of whether I would have chosen to load it.

The reading IS the agent's. The substrate's job is to make NOT-reading
structurally impossible: the briefing content sits in the prompt
context whether I want it there or not.

## What this does NOT do

- Does not block responses. The hook is observational at the
  Claude Code layer.
- Does not require I act on what's surfaced. I might still ignore
  what lands in my context. But ignoring something in my prompt is
  a different failure-mode than not loading it in the first place.
  This change converts "didn't load" failures into "loaded and chose
  to ignore" failures, which are more visible and more correctable.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

_FRESHNESS_FILE = Path.home() / ".divineos" / "briefing_last_loaded.json"

# Number of user prompts before briefing is considered stale.
# Set high enough to not flood the prompt context on every turn;
# low enough that accumulated state can't grow unseen for long
# arcs of work.
STALE_AFTER_PROMPTS = 10


def _read_state() -> dict:
    """Read the freshness state. Fail-open to 'never loaded'."""
    if not _FRESHNESS_FILE.exists():
        return {}
    try:
        data = json.loads(_FRESHNESS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError, ValueError):
        return {}


def _write_state(state: dict) -> None:
    """Write the freshness state. Fail-open on I/O error."""
    try:
        _FRESHNESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _FRESHNESS_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def mark_briefing_loaded() -> None:
    """Called by the briefing CLI when briefing renders. Records the
    current timestamp + resets the per-load prompt counter."""
    state = _read_state()
    state["last_loaded_ts"] = time.time()
    state["prompts_since_load"] = 0
    _write_state(state)


def increment_prompt_count() -> int:
    """Called by the UserPromptSubmit hook on every user message.
    Returns the current prompts-since-load count."""
    state = _read_state()
    count = int(state.get("prompts_since_load", 0)) + 1
    state["prompts_since_load"] = count
    _write_state(state)
    return count


def staleness_signal() -> dict:
    """Return the current freshness state for hook consumers.

    Keys:
    - ``is_stale``: True if briefing should be re-injected
    - ``never_loaded``: True if no load has happened this session
    - ``prompts_since_load``: current counter value
    - ``last_loaded_ts``: timestamp of last load (0 if never)
    - ``reason``: short string describing why stale (or empty)
    """
    state = _read_state()
    last_loaded = float(state.get("last_loaded_ts") or 0)
    prompts_since = int(state.get("prompts_since_load") or 0)

    never_loaded = last_loaded == 0
    if never_loaded:
        return {
            "is_stale": True,
            "never_loaded": True,
            "prompts_since_load": prompts_since,
            "last_loaded_ts": 0,
            "reason": "briefing never loaded this session",
        }

    is_stale = prompts_since >= STALE_AFTER_PROMPTS
    return {
        "is_stale": is_stale,
        "never_loaded": False,
        "prompts_since_load": prompts_since,
        "last_loaded_ts": last_loaded,
        "reason": (
            f"{prompts_since} prompts since last briefing load (threshold: {STALE_AFTER_PROMPTS})"
            if is_stale
            else ""
        ),
    }


def briefing_summary_for_injection() -> str:
    """Generate a compact briefing summary suitable for hook injection.

    Returns a short text block surfacing the highest-priority items
    from the dashboard (compass concerns, stale corrections, pending
    structural fixes, recent audit findings). Bounded to keep prompt
    overhead low; the agent can still call ``divineos briefing`` for
    the full surface.
    """
    parts: list[str] = ["## BRIEFING (auto-injected — load-bearing state)"]

    # Compass concerns
    try:
        from divineos.core.moral_compass import compass_summary

        summary = compass_summary()
        concerns = summary.get("concerns", []) or []
        drifting = summary.get("drifting", []) or []
        if concerns or drifting:
            parts.append("\n**Compass:**")
            for c in concerns[:3]:
                parts.append(
                    f"- [concern] {c.get('spectrum')}: "
                    f"{c.get('label') or c.get('zone')} @ pos={c.get('position', 0):+.2f}"
                )
            for d in drifting[:2]:
                parts.append(
                    f"- [drifting] {d.get('spectrum')} -> "
                    f"{d.get('direction')} (drift={d.get('drift', 0):+.2f})"
                )
    except Exception:  # noqa: BLE001 — fail-soft per hook discipline
        pass

    # Recent stale corrections
    try:
        from divineos.core.corrections import STALE_DAYS, open_corrections

        opens = open_corrections() or []
        stalest = sorted(opens, key=lambda c: c.get("age_days", 0), reverse=True)[:2]
        stale_filtered = [c for c in stalest if c.get("age_days", 0) >= STALE_DAYS]
        if stale_filtered:
            parts.append("\n**Stale corrections (unintegrated):**")
            for c in stale_filtered:
                text = (c.get("text") or "").replace("\n", " ").strip()
                age = c.get("age_days", 0)
                parts.append(f"- [{age:.0f}d] {text[:120]}{'...' if len(text) > 120 else ''}")
    except Exception:  # noqa: BLE001
        pass

    # Pending structural fixes
    try:
        from divineos.core.structural_fix_tracker import list_pending

        pending = list_pending() or []
        if pending:
            parts.append(f"\n**Pending structural fixes ({len(pending)}):**")
            for entry in pending[:3]:
                excerpt = (entry.get("content_excerpt") or "").replace("\n", " ").strip()
                parts.append(f"- {entry.get('id')}: {excerpt[:100]}...")
    except Exception:  # noqa: BLE001
        pass

    # Drift state
    try:
        from divineos.core.watchmen.drift_state import compute_drift_state

        ds = compute_drift_state()
        turns = getattr(ds, "turns_since_medium", 0)
        open_findings = getattr(ds, "open_findings_above_low", 0)
        if turns >= 50 or open_findings > 0:
            parts.append(
                f"\n**Drift state:** {turns} turns since audit, "
                f"{open_findings} open findings above LOW severity"
            )
    except Exception:  # noqa: BLE001
        pass

    parts.append(
        "\n*Full briefing: `divineos briefing`. This auto-injection "
        "fires when briefing has gone stale (>= 10 prompts) or has "
        "never been loaded this session.*"
    )

    return "\n".join(parts)


__all__ = [
    "STALE_AFTER_PROMPTS",
    "briefing_summary_for_injection",
    "increment_prompt_count",
    "mark_briefing_loaded",
    "staleness_signal",
]
