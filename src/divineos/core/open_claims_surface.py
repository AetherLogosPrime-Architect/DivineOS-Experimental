"""Stale-open-claims surface — bridge from the claims store to the briefing.

## Why this module exists

DivineOS already surfaces overdue pre-regs in the briefing. Pre-regs
are *time-bound* — they have an explicit review date, and the surface
fires when that date passes. Claims have no review date. They sit in
``status=OPEN`` until someone resolves them, and the briefing has no
path to them.

A real failure mode observed during the 2026-04-24 audit pass: the
claims store accumulated 38 OPEN claims across 2 days, **none
resolved**, with no surface telling the agent "you have 38
investigations awaiting evidence." Investigations filed-and-forgotten
are the recall hole the meta-pattern (claim-filed-without-behavior-
change) names — except here the failure isn't recurrence, it's
silent accumulation.

This module closes that gap. Same descriptive-only pattern as
``in_flight_branches``, ``module_inventory``, ``upstream_freshness``:
read the claims table, surface a compact view, leave reading and
prioritization to the session that reads it.

## Shape

The block has two parts:

  1. **Headline count** — total OPEN claims, plus how many are
     older than the staleness threshold. Always informative; even
     when nothing is stale, the count tells the agent how many open
     investigations exist.
  2. **Stale claims list** — the oldest open claims, capped at 10,
     with claim_id prefix + tier + age in days + truncated
     statement. Recognition prompts; full claim contents available
     via ``divineos claims show <id>``.

## What this module does NOT do

* Does not interpret which claims are most important. Age and tier
  are objective; importance is judgment, and the briefing leaves
  judgment to the reader.
* Does not auto-resolve claims. The investigation-then-assessment
  workflow is a deliberate path; this surface only makes the queue
  visible.
* Does not load the full claim text. Statement is truncated at 100
  chars; full contents are one CLI call away.

## Pattern

Mirrors ``in_flight_branches.format_for_briefing``,
``module_inventory.format_for_briefing``, and
``upstream_freshness.format_for_briefing``: a plain formatter that
emits a named block when there is something to surface, returns
empty string otherwise.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

# Claims older than this threshold are surfaced individually as the
# "stale" subset of the open queue. 7 days is a deliberate choice:
# investigations that haven't moved in a week are the ones most at
# risk of being forgotten entirely. Shorter threshold spams the
# briefing with normal in-progress work; longer hides forgotten
# investigations until they've already drifted out of memory.
STALENESS_THRESHOLD_DAYS = 7

# Cap on individual claim entries surfaced. The headline count
# always shows the total; the list shows the OLDEST N for action.
# 10 is large enough to reveal the spread of stale work without
# bloating the briefing.
MAX_LISTED_CLAIMS = 10

# Below this total, the surface stays silent — a small number of
# fresh open claims is the normal working state, not signal.
MIN_OPEN_CLAIMS_TO_SURFACE = 3


@dataclass(frozen=True)
class OpenClaim:
    """One row in the stale-claims surface."""

    claim_id: str
    tier: int
    statement: str
    age_days: float


def _list_open_claims_safe() -> list[dict]:
    """Pull open claims from the store, returning [] on any failure.

    The briefing must never break because the claims store is
    unavailable or its schema has shifted. Returns an empty list and
    lets the caller emit empty string.
    """
    try:
        from divineos.core.claim_store import list_claims
    except ImportError:
        return []
    try:
        rows = list_claims(limit=500, status="OPEN")
    except TypeError:
        # Older signatures may not accept status= kwarg; fall back to
        # filter post-fetch.
        try:
            rows = list_claims(limit=500)
        except Exception:  # noqa: BLE001
            return []
        rows = [r for r in rows if r.get("status") == "OPEN"]
    except Exception:  # noqa: BLE001
        return []
    return [r for r in rows if isinstance(r, dict)]


def _coerce_age_days(created_at, now: float) -> float:
    """Compute age in days from a created_at timestamp. Returns 0 on failure."""
    if created_at is None:
        return 0.0
    try:
        ts = float(created_at)
    except (TypeError, ValueError):
        return 0.0
    if ts <= 0:
        return 0.0
    return max(0.0, (now - ts) / 86400.0)


def _to_open_claim(row: dict, now: float) -> OpenClaim | None:
    """Project a store row to an OpenClaim. Returns None when unusable."""
    claim_id = str(row.get("claim_id") or "").strip()
    if not claim_id:
        return None
    statement = str(row.get("statement") or "").strip()
    if not statement:
        return None
    try:
        tier = int(row.get("tier") or 0)
    except (TypeError, ValueError):
        tier = 0
    age = _coerce_age_days(row.get("created_at"), now)
    return OpenClaim(claim_id=claim_id, tier=tier, statement=statement, age_days=age)


def format_for_briefing() -> str:
    """Return a briefing block for stale open claims, or empty string.

    Empty when fewer than MIN_OPEN_CLAIMS_TO_SURFACE open claims exist
    OR the claim store is unreachable. Otherwise the block names the
    total open count, the count of stale (>STALENESS_THRESHOLD_DAYS),
    and lists the oldest MAX_LISTED_CLAIMS claims as recognition
    prompts.
    """
    rows = _list_open_claims_safe()
    if len(rows) < MIN_OPEN_CLAIMS_TO_SURFACE:
        return ""

    now = time.time()
    claims = [c for c in (_to_open_claim(r, now) for r in rows) if c is not None]
    if not claims:
        return ""

    claims.sort(key=lambda c: c.age_days, reverse=True)
    stale_count = sum(1 for c in claims if c.age_days >= STALENESS_THRESHOLD_DAYS)

    plural = "claim" if len(claims) == 1 else "claims"
    headline = f"[open claims] {len(claims)} open investigation {plural}"
    if stale_count:
        stale_plural = "is" if stale_count == 1 else "are"
        headline += f" — {stale_count} {stale_plural} older than {STALENESS_THRESHOLD_DAYS} days"
    headline += ":"

    lines = [headline]
    for c in claims[:MAX_LISTED_CLAIMS]:
        snippet = c.statement if len(c.statement) <= 100 else c.statement[:97] + "..."
        prefix = c.claim_id[:8]
        marker = " STALE" if c.age_days >= STALENESS_THRESHOLD_DAYS else ""
        lines.append(f"  - {prefix}... T{c.tier} ({c.age_days:.1f}d{marker}) — {snippet}")
    if len(claims) > MAX_LISTED_CLAIMS:
        lines.append(f"  +{len(claims) - MAX_LISTED_CLAIMS} more open claim(s).")
    lines.append(
        "  Recognition prompt only. `divineos claims show <id>` for full text;"
        " `divineos claims assess <id> ...` to update status."
    )

    return "\n".join(lines) + "\n"


__all__ = [
    "format_for_briefing",
    "OpenClaim",
    "STALENESS_THRESHOLD_DAYS",
    "MAX_LISTED_CLAIMS",
    "MIN_OPEN_CLAIMS_TO_SURFACE",
]
