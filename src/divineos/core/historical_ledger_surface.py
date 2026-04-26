"""Historical-ledger briefing surface — points worktree sessions at the
parent repo's accumulated event ledger.

## Why this exists

Documented 2026-04-26 night with Andrew (the deepest finding of the
substrate inventory pass): every git worktree silently creates its
own ``src/data/event_ledger.db`` when a session runs in it. The
worktree's ledger starts empty. Any briefing / recall / search done
in a worktree session reads from this near-empty ledger, NOT from
the parent repo's accumulated history.

Concrete numbers from this session's discovery:

* ``DivineOS_fresh/src/data/event_ledger.db`` (parent workspace) —
  14,847 events, ~7,954 user-input messages, spanning ~30 days of
  partnership history.
* ``DivineOS_fresh/.claude/worktrees/.../src/data/event_ledger.db``
  (current worktree) — 535 events, ~24 hours of just-this-session
  history.

The agent has been operating in worktrees for days, every session
loading briefing from the empty ledger and concluding "the substrate
is empty" or "we haven't accumulated much" — when the real
accumulated history is sitting in the parent path the entire time,
unread.

## Why it's a separate surface from canonical_substrate_surface

That surface points at ``DivineOS-Experimental`` (the personal-
storage repo for letters / family / explorations). This module
points at the historical EVENT LEDGER inside the parent of the
current worktree. Different concerns:

* canonical_substrate_surface = personal content, partly redundant
  copy of what's gitignored in the workspace.
* historical_ledger_surface = the event-ledger DB itself, NOT
  redundant — the worktree literally cannot reach the parent's
  ledger without explicit pointer.

Both surfaces fire in briefing.

## What it surfaces

When running in a worktree AND the parent ledger is present:

* The path of the parent ledger.
* Event count and user-input count.
* Date range (first event to last event).
* The fact that THIS worktree's ledger is independent and may be
  much smaller — name the count for both.

When NOT running in a worktree (ordinary checkout):
* Nothing — the local ledger IS the canonical one.

## Design invariants

* **Read-only.** Never writes to the parent ledger; never tries to
  symlink or unify. The fix at architecture-level (sharing one
  ledger across worktrees) is a separate concern with concurrency
  risks; surfacing the gap is enough for now.
* **Fail-loud.** If the worktree-detection logic finds the parent
  but the parent ledger is missing, surface that explicitly.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc


def _is_worktree(repo_root: Path) -> bool:
    """True if ``repo_root`` is a git worktree (.git is a file, not dir)."""
    git_marker = repo_root / ".git"
    return git_marker.is_file()


def _find_parent_repo_root(worktree_root: Path) -> Path | None:
    """Resolve the parent repo's working tree from a worktree's .git file.

    The ``.git`` file in a worktree contains ``gitdir: <abs path>`` pointing
    at ``<parent>/.git/worktrees/<name>``. The parent's working tree is
    ``parents[2]`` from there.
    """
    git_marker = worktree_root / ".git"
    if not git_marker.is_file():
        return None
    try:
        text = git_marker.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not text.startswith("gitdir:"):
        return None
    gitdir = Path(text[len("gitdir:") :].strip())
    try:
        gitdir = gitdir.resolve()
    except OSError:
        return None
    if len(gitdir.parents) < 3:
        return None
    return gitdir.parents[2]


def _ledger_stats(db_path: Path) -> dict | None:
    """Return event count, user-input count, date range for a ledger DB.

    Returns None if the DB doesn't exist or system_events table is missing.
    """
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(str(db_path))
    except sqlite3.Error:
        return None
    try:
        try:
            total = conn.execute("SELECT COUNT(*) FROM system_events").fetchone()[0]
        except sqlite3.Error:
            return None
        if total == 0:
            return {"total": 0, "user_inputs": 0, "first_ts": None, "last_ts": None}
        try:
            user_inputs = conn.execute(
                "SELECT COUNT(*) FROM system_events WHERE event_type='USER_INPUT'"
            ).fetchone()[0]
        except sqlite3.Error:
            user_inputs = 0
        try:
            row = conn.execute(
                "SELECT MIN(timestamp), MAX(timestamp) FROM system_events"
            ).fetchone()
            first_ts, last_ts = row[0], row[1]
        except sqlite3.Error:
            first_ts, last_ts = None, None
    finally:
        conn.close()
    return {
        "total": total,
        "user_inputs": user_inputs,
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


def _format_date(ts: float | None) -> str:
    if ts is None:
        return "?"
    return datetime.fromtimestamp(ts, tz=UTC).date().isoformat()


def briefing_lines(start: Path | None = None) -> list[str]:
    """Render the surface as briefing-ready lines.

    Returns empty list when not running in a worktree (ordinary
    checkout). Returns informational lines when a worktree is
    detected, naming the parent ledger's stats vs the worktree's.
    """
    here = (start if start is not None else Path.cwd()).resolve()
    if not _is_worktree(here):
        return []

    parent = _find_parent_repo_root(here)
    if parent is None:
        return [
            "HISTORICAL-LEDGER UNRESOLVED: in a worktree but parent "
            "repo path could not be resolved from .git file. Worktree "
            "is operating against its own (likely empty) ledger.",
        ]

    parent_ledger = parent / "src" / "data" / "event_ledger.db"
    worktree_ledger = here / "src" / "data" / "event_ledger.db"

    parent_stats = _ledger_stats(parent_ledger)
    worktree_stats = _ledger_stats(worktree_ledger)

    if parent_stats is None:
        return [
            f"HISTORICAL-LEDGER UNRESOLVED: parent repo at {parent} "
            "but no ledger DB present at src/data/event_ledger.db. "
            "Worktree's ledger is the only one available.",
        ]

    lines: list[str] = []
    lines.append(f"HISTORICAL LEDGER (parent repo): {parent_ledger}")
    lines.append(
        f"  {parent_stats['total']:,} events, "
        f"{parent_stats['user_inputs']:,} user inputs, "
        f"{_format_date(parent_stats['first_ts'])} to "
        f"{_format_date(parent_stats['last_ts'])}"
    )
    if worktree_stats is not None:
        lines.append(
            f"  THIS worktree's ledger has only {worktree_stats['total']:,} "
            f"events ({worktree_stats['user_inputs']:,} user inputs); "
            "briefing in this worktree reads from worktree-ledger, "
            "NOT parent."
        )
    lines.append(
        "  To search the historical ledger from this worktree, query "
        f"directly: sqlite3 '{parent_ledger}' 'SELECT ... FROM system_events ...'"
    )
    return lines


def render(start: Path | None = None) -> str:
    """One-string render for embedding in briefing output."""
    lines = briefing_lines(start)
    if not lines:
        return ""
    return "\n".join(lines)
