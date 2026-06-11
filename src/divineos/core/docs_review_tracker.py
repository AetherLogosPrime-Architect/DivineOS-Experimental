"""Docs-architecture sync tracker — surface drift between code and docs.

Andrew 2026-06-10 reframe of the doc-count leapfrog problem: the goal
is NOT to auto-generate doc counts (that hides drift behind machinery
and is the wrong shape — ``check_doc_counts.py --fix`` blindly overwrites
without my judgment, which is why PR #129 made it opt-in). The goal IS
to make the agent **notice** when architecture has shifted since the
docs were last reviewed, and route the agent to do the judgment-work
of reading the docs and updating with intent.

Counts are a proxy. Content currency is the real thing. A README that
says "517 source files across 31 packages" is true at filing time;
what matters is whether the prose still **describes** what's actually
there now. Numbers drift loudly (the gate catches them); content drifts
silently (no gate catches that, only periodic human-style review does).

This module provides the substrate primitives for a review-discipline
gate that doesn't auto-fix and doesn't substitute for thinking — it
surfaces the gap and routes the agent to close it manually.

## Surfaces

- ``mark_reviewed(actor, notes='', files=None)`` — record a
  ``DOCS_REVIEWED`` event in the ledger. Captures the reviewer, the
  current commit SHA, optional notes about what was changed, and the
  list of doc files reviewed (defaults to the standard set).
- ``last_review()`` — return the most recent DOCS_REVIEWED event, or
  None if no review has been recorded.
- ``architecture_churn_since(commit_sha)`` — list files added/modified/
  removed under ``src/divineos/`` and ``.claude/hooks/`` between
  ``commit_sha`` and HEAD. Empty list means no architectural change.
- ``review_status(threshold_days=7, threshold_files=20)`` — composite
  surface returning a dict suitable for the briefing row:
  ``{stale, age_days, churn_count, last_actor, last_commit}``.

## Wiring (next step, not in this module)

The briefing dashboard (``core/briefing_dashboard.py``) should add a
row that calls ``review_status()`` and surfaces stale-review state.
The pre-commit hook can optionally call ``review_status()`` as an
advisory (NOT a block — Andrew 2026-06-10 GATE-AS-CHANNEL: the path
is review-then-mark, not auto-fix-and-bypass-judgment). Both wirings
are intentionally out of this module's scope so the substrate primitive
ships small and testable; the briefing-row builder is the high-risk
surface area and lands separately.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

_DEFAULT_DOC_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "docs/ARCHITECTURE.md",
)
_DEFAULT_ARCH_PATHS: tuple[str, ...] = ("src/divineos/", ".claude/hooks/")


def _current_head_sha() -> str | None:
    """Return ``git rev-parse HEAD`` or None on failure (fail-soft)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    return sha or None


def mark_reviewed(
    actor: str,
    notes: str = "",
    files: tuple[str, ...] | None = None,
) -> str:
    """Record a DOCS_REVIEWED event in the ledger. Returns the event_id.

    The event captures actor + current HEAD SHA + notes + reviewed-file
    list. Stored events are queryable via ``last_review()`` so the
    briefing-row builder can compute time-since-last-review and
    architecture-churn-since-last-review.
    """
    from divineos.core.ledger import log_event

    payload: dict[str, Any] = {
        "head_sha": _current_head_sha() or "",
        "notes": notes,
        "files": list(files or _DEFAULT_DOC_FILES),
        "ts": time.time(),
    }
    return log_event("DOCS_REVIEWED", actor, payload, validate=False)


def last_review() -> dict | None:
    """Return the most recent DOCS_REVIEWED event payload + metadata,
    or None if no review has been recorded.

    Returned dict carries ``ts`` (timestamp), ``head_sha`` (commit at
    review time), ``actor`` (who marked), ``notes``, and ``files``.
    """
    try:
        from divineos.core.ledger import get_events
    except ImportError:
        return None
    try:
        events = get_events(limit=50, event_type="DOCS_REVIEWED")
    except Exception:  # noqa: BLE001 — fail-soft on ledger trouble
        return None
    if not events:
        return None
    # get_events returns newest-first per the ASC-vs-DESC fix in PR #135.
    latest = events[0]
    payload = latest.get("payload") or {}
    if isinstance(payload, str):
        import json

        try:
            payload = json.loads(payload)
        except (TypeError, ValueError):
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return {
        "ts": float(payload.get("ts") or latest.get("timestamp") or 0),
        "head_sha": str(payload.get("head_sha") or ""),
        "actor": str(latest.get("actor") or ""),
        "notes": str(payload.get("notes") or ""),
        "files": list(payload.get("files") or []),
    }


def architecture_churn_since(
    commit_sha: str,
    arch_paths: tuple[str, ...] = _DEFAULT_ARCH_PATHS,
) -> list[str]:
    """Return files under ``arch_paths`` that changed between
    ``commit_sha`` and HEAD. Empty list when no change.

    Uses ``git diff --name-only <sha>..HEAD -- <paths>``. Fail-soft:
    returns an empty list on any git error so an unreadable git
    state doesn't break callers' briefing rendering.
    """
    if not commit_sha:
        return []
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{commit_sha}..HEAD", "--", *arch_paths],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.strip().split("\n") if line.strip()]


def review_status(
    threshold_days: float = 7.0,
    threshold_files: int = 20,
) -> dict:
    """Composite status for the briefing row.

    Returns a dict the briefing-row builder can render directly:

      stale: bool         — true if review is overdue by EITHER axis
      age_days: float     — days since last review, or float('inf')
      churn_count: int    — number of arch files changed since review
      churn_files: list   — names of changed arch files (capped at 20)
      last_actor: str     — who last marked, or ""
      last_commit: str    — SHA at last review, or ""
      reason: str         — short human-readable reason for stale=True

    Empty/missing last-review treats EITHER axis as immediately stale —
    a never-reviewed substrate should not pass as fresh.
    """
    last = last_review()
    if last is None:
        return {
            "stale": True,
            "age_days": float("inf"),
            "churn_count": 0,
            "churn_files": [],
            "last_actor": "",
            "last_commit": "",
            "reason": "no DOCS_REVIEWED event has ever been recorded",
        }

    age_days = (time.time() - last["ts"]) / 86400 if last["ts"] else float("inf")
    churn = architecture_churn_since(last["head_sha"]) if last["head_sha"] else []
    churn_count = len(churn)

    reasons = []
    if age_days > threshold_days:
        reasons.append(f"{age_days:.1f}d since last review (> {threshold_days}d)")
    if churn_count > threshold_files:
        reasons.append(f"{churn_count} arch files changed (> {threshold_files})")
    stale = bool(reasons)

    return {
        "stale": stale,
        "age_days": age_days,
        "churn_count": churn_count,
        "churn_files": churn[:20],
        "last_actor": last["actor"],
        "last_commit": last["head_sha"],
        "reason": "; ".join(reasons) if reasons else "current",
    }
