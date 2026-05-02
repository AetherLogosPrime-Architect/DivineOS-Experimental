"""Goal-outcome briefing surface — action-loop closure for session goals.

## Why this module exists

Per claim 5b38a31c (PORT-CANDIDATE 5 from old-OS strip-mine, salvaged
from `module specs/ACTION LOOP CLOSURE 15.7.txt`): the new OS files
session goals + decisions + claims, but items get **filed without
outcomes getting systematically compared back**. Goals get added,
worked-around-or-not, then aged out — and `auto_clean_goals` used to
silently mark stale goals as "done" and increment the lifetime
completion counter. That was a goodhart-shape: timeout-archival
inflated completion stats.

The action-loop closure response: when goals exit the active list via
timeout or dedup (i.e., not via `complete_goal` which signals real
completion), record the outcome to `goal_outcomes.json` and surface
recent stale-archivals at next session start. This is the
prediction-error feedback the old-OS spec described, scoped to
session-goals as the smallest meaningful Phase 1.

## Shape

A briefing block, only when there are stale-archived goals from recent
sessions:

  [goals that aged out without progression]
    "Build per-session briefing-load gate" — added 2d ago, archived 1d ago
    "Continue strip-mine reading pass" — added 3d ago, archived 2d ago
    consider: was this goal abandoned deliberately, or did it slip?

The "consider:" line is recognition prompt — operator/agent decides
whether to refile, mark genuinely-abandoned, or ignore.

## What this module does NOT do

* Does not refile goals automatically. Stale-archival might be
  legitimate (priorities shifted, work happened in a different shape).
  The surface displays; the operator/agent decides.
* Does not show goals that exited via `complete_goal` — those are real
  completions and don't need to be re-litigated.
* Does not surface anything if there are zero recent stale-archivals.
  No-news is fine; this surface is targeted at the failure mode of
  goals timing out without recorded progression.

## Pattern

Mirrors `council_balance_surface.format_for_briefing` and
`open_claims_surface.format_for_briefing`: a plain formatter that
emits a named block when there is something to surface, empty string
otherwise. Fail-soft on any error.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# Window for which stale-archivals are surfaced. Older entries fall off.
# 7 days matches open_claims_surface staleness threshold.
SURFACE_WINDOW_DAYS = 7

# Cap on listed entries to prevent the briefing block from bloating
# when many goals timed out simultaneously.
MAX_LISTED = 5

# Below this many recent stale-archivals, the surface stays silent.
# Surfacing one stale goal would generate noise; the pattern needs at
# least a couple of instances to be worth surfacing.
MIN_TO_SURFACE = 2


def _outcomes_path() -> Path:
    """Locate goal_outcomes.json in the same hud dir hud_state writes to."""
    # Match _ensure_hud_dir() in hud_state.py — keep the path resolution
    # local so this module doesn't import from hud_state (avoids
    # circular-import risk).
    return Path.home() / ".divineos" / "hud" / "goal_outcomes.json"


def _format_age(seconds: float) -> str:
    """Format seconds as a short human-readable age string."""
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    if seconds < 86400:
        return f"{int(seconds / 3600)}h"
    return f"{int(seconds / 86400)}d"


def format_for_briefing() -> str:
    """Return the briefing block for stale-archived goals, or empty string.

    Empty when:
    * No outcomes file exists yet
    * Fewer than MIN_TO_SURFACE recent stale-archivals
    * Any internal failure (briefing must not break)
    """
    try:
        path = _outcomes_path()
        if not path.exists():
            return ""

        outcomes = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(outcomes, list):
            return ""

        now = time.time()
        cutoff = now - (SURFACE_WINDOW_DAYS * 86400.0)

        stale = [
            o
            for o in outcomes
            if isinstance(o, dict)
            and o.get("outcome") == "stale_archived"
            and o.get("archived_at", 0) >= cutoff
        ]

        if len(stale) < MIN_TO_SURFACE:
            return ""

        # Newest stale-archivals first
        stale.sort(key=lambda o: o.get("archived_at", 0), reverse=True)
        listed = stale[:MAX_LISTED]

        lines = [f"[goals that aged out without progression — last {SURFACE_WINDOW_DAYS}d]"]
        for o in listed:
            text = o.get("text", "")[:80]
            added_age = _format_age(now - o.get("added_at", now))
            archived_age = _format_age(now - o.get("archived_at", now))
            lines.append(f'  "{text}" — added {added_age} ago, archived {archived_age} ago')

        if len(stale) > MAX_LISTED:
            lines.append(f"  ... +{len(stale) - MAX_LISTED} more this window")

        lines.append("  consider: was each goal abandoned deliberately, or did it slip?")
        return "\n".join(lines)
    except Exception:  # noqa: BLE001 — briefing must never break on this surface
        return ""
