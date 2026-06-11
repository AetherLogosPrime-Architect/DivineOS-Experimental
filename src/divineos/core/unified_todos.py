"""Unified todos surface — pull observable-state work into one ranked list.

Closes claim 2026-06-06 18:28 (T1:empirical): "the goal/todo system is a
manual .md file rather than an OS-driven instrument: filing and closing
both require intent, and the OS does not generate todos from its own
observable state (failing tests, overdue preregs, unresolved audit
findings, drift), pushing the burden of finding-the-work onto Andrew."

The substrate already has work spread across five stores — preregs,
Andrew-corrections, audit findings, claims, lessons. None of them is
THE todo list; together they are. Tonight's "what else is on the todo
list?" question landed on me as ambiguous because I had to query five
places, mentally filter recognition-noise out of audit, and then
guess at ranking. The right shape: one function that does that for me.

## What this surfaces

- **preregs** filed and still OPEN, sorted by review_ts ascending so
  most-overdue surface first (overdue review = ship-the-mechanism or
  explicitly defer; the prereg system itself enforces this elsewhere
  but the todo list should pre-rank by it).
- **Andrew-corrections** still OPEN, sorted oldest first (the
  attribution surface already does this; we just expose it here).
- **audit findings** still OPEN, **recognition-filtered** — titles
  beginning with ``CONFIRMS`` or ``RECOGNIZED`` are recognitions, not
  action-items, and the unified list must not surface them as work.
  Recognition-aware aggregate is the same discipline the briefing
  dashboard uses; the todos surface inherits it.
- **claims** still OPEN, **action-tier filtered** — only T1:empirical
  and T2:observational map to "investigate this" work; T3:contested,
  T4:speculative, T5:metaphysical are positions to track, not action
  items to chase.

Lessons are intentionally out of scope for v1: active lessons are
behavioral patterns rather than discrete pieces of work and would
inflate the list with non-actionable items. If a lesson grows into a
concrete fix, it shows up as a prereg or claim already.

## Return shape

``collect_todos()`` returns ``list[TodoItem]`` — one row per work item
across all sources. Each row carries source, id, summary, age_days,
and priority hint. The CLI renderer groups by source and sorts within
each group by the source-appropriate key (overdue-ness for preregs,
age for corrections, severity for findings, tier for claims).

The function is pure (reads from substrate, returns data). The CLI is
the surface that calls it and prints — same separation as the rest of
the briefing-row builders.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


_RECOGNITION_TITLE_PREFIXES: tuple[str, ...] = ("confirms", "recognized")
_ACTION_TIER_RANK: dict[str, int] = {
    # Tier names → todo-priority rank (lower = higher priority). Only
    # tiers that map to "go investigate this" are included; speculative
    # / metaphysical / contested are positions to track, not action items.
    "T1:empirical": 1,
    "T1": 1,
    "empirical": 1,
    "T2:observational": 2,
    "T2": 2,
    "observational": 2,
}


@dataclass
class TodoItem:
    """One todo across the unified surface."""

    source: str  # "prereg" | "correction" | "audit" | "claim"
    item_id: str
    summary: str
    age_days: float | None  # may be None when the source doesn't expose age
    priority: int  # lower = higher priority within source
    extra: dict[str, Any]  # source-specific metadata (review_ts, severity, etc.)


def _safe_age_days(ts: float | None, now: float | None = None) -> float | None:
    if ts is None or ts <= 0:
        return None
    base = now if now is not None else time.time()
    return max(0.0, (base - float(ts)) / 86400)


def _is_recognition_title(title: str) -> bool:
    """True if a finding title reads as a recognition (CONFIRMS / RECOGNIZED)
    rather than an action-item finding. Recognition-aware aggregate per the
    audit-system convention (docs/audit_system.md)."""
    if not title:
        return False
    head = title.strip().lower()
    return any(head.startswith(prefix) for prefix in _RECOGNITION_TITLE_PREFIXES)


def _prereg_todos(limit: int = 500, now: float | None = None) -> list[TodoItem]:
    """Pull OPEN preregs, ranked by most-overdue first."""
    try:
        from divineos.core.pre_registrations.store import list_pre_registrations
        from divineos.core.pre_registrations.types import Outcome
    except ImportError:
        return []
    try:
        rows = list_pre_registrations(outcome=Outcome.OPEN, limit=limit)
    except Exception:  # noqa: BLE001 — fail-soft per substrate convention
        return []
    base = now if now is not None else time.time()
    items: list[TodoItem] = []
    for p in rows:
        review_ts = float(getattr(p, "review_ts", 0) or 0)
        overdue_days = (base - review_ts) / 86400 if review_ts > 0 else 0
        # Priority: ranked by review_ts ascending so most-overdue first.
        # Use int(-overdue_days * 1000) so a more-overdue prereg gets a
        # lower (more-priority) sort key.
        priority = int(-overdue_days * 1000) if overdue_days > 0 else 0
        items.append(
            TodoItem(
                source="prereg",
                item_id=str(getattr(p, "prereg_id", "")),
                summary=str(getattr(p, "mechanism", ""))[:200],
                age_days=_safe_age_days(getattr(p, "created_at", None), now),
                priority=priority,
                extra={
                    "review_ts": review_ts,
                    "overdue_days": overdue_days,
                    "actor": str(getattr(p, "actor", "")),
                },
            )
        )
    items.sort(key=lambda t: t.priority)
    return items


def _correction_todos(now: float | None = None) -> list[TodoItem]:
    """Pull OPEN Andrew-corrections, oldest first."""
    try:
        from divineos.core.andrew_correction_tracker import list_open
    except ImportError:
        return []
    try:
        rows = list_open()
    except Exception:  # noqa: BLE001
        return []
    items: list[TodoItem] = []
    for r in rows:
        ts = r.get("filed_at") or r.get("ts") or 0
        try:
            ts = float(ts)
        except (TypeError, ValueError):
            ts = 0
        age = _safe_age_days(ts, now)
        items.append(
            TodoItem(
                source="correction",
                item_id=str(r.get("id") or r.get("correction_id") or ""),
                summary=str(r.get("text") or r.get("description") or "")[:200],
                age_days=age,
                priority=int(-(age or 0) * 1000),  # oldest first
                extra={"filed_at": ts},
            )
        )
    items.sort(key=lambda t: t.priority)
    return items


def _audit_todos(limit: int = 100, now: float | None = None) -> list[TodoItem]:
    """Pull OPEN audit findings, recognition-filtered (CONFIRMS /
    RECOGNIZED titles excluded — they're acknowledgements, not action
    items)."""
    try:
        from divineos.core.watchmen.store import list_findings
    except ImportError:
        return []
    try:
        rows = list_findings(status="OPEN", limit=limit)
    except Exception:  # noqa: BLE001
        return []
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    items: list[TodoItem] = []
    for f in rows:
        title = getattr(f, "title", "") or ""
        if _is_recognition_title(title):
            continue
        sev = str(getattr(f, "severity", "INFO"))
        sev_key = sev.value if hasattr(sev, "value") else str(sev)
        ts = getattr(f, "created_at", None) or getattr(f, "timestamp", None)
        try:
            ts = float(ts) if ts is not None else None
        except (TypeError, ValueError):
            ts = None
        items.append(
            TodoItem(
                source="audit",
                item_id=str(getattr(f, "finding_id", "")),
                summary=title[:200],
                age_days=_safe_age_days(ts, now),
                priority=severity_rank.get(sev_key, 5),
                extra={
                    "severity": sev_key,
                    "category": str(getattr(f, "category", "")),
                },
            )
        )
    items.sort(key=lambda t: t.priority)
    return items


def _claim_todos(limit: int = 100, now: float | None = None) -> list[TodoItem]:
    """Pull OPEN claims, action-tier filtered (only T1/T2 are action
    items; higher tiers are positions to track)."""
    try:
        from divineos.core.claim_store import list_claims
    except ImportError:
        return []
    try:
        rows = list_claims(status="OPEN", limit=limit)
    except Exception:  # noqa: BLE001
        return []
    items: list[TodoItem] = []
    for c in rows:
        tier = str(c.get("tier") or "")
        rank = _ACTION_TIER_RANK.get(tier)
        if rank is None:
            # Non-action tier; skip from the todos surface.
            continue
        ts = c.get("filed_at") or c.get("created_at") or c.get("timestamp")
        try:
            ts = float(ts) if ts is not None else None
        except (TypeError, ValueError):
            ts = None
        items.append(
            TodoItem(
                source="claim",
                item_id=str(c.get("claim_id") or c.get("id") or ""),
                summary=str(c.get("statement") or c.get("content") or "")[:200],
                age_days=_safe_age_days(ts, now),
                priority=rank,
                extra={"tier": tier, "confidence": c.get("confidence")},
            )
        )
    items.sort(key=lambda t: (t.priority, t.age_days or 0))
    return items


def collect_todos(
    sources: tuple[str, ...] | None = None,
    now: float | None = None,
) -> list[TodoItem]:
    """Pull all action-items across the requested sources into one list.

    ``sources`` restricts which stores are queried; default is all four
    (``"prereg"``, ``"correction"``, ``"audit"``, ``"claim"``). Order
    of returned items: grouped by source in the order requested, then
    sorted within each group by the source-appropriate priority key
    (most-overdue prereg first, oldest correction first, highest-
    severity audit finding first, action-tier claim first).
    """
    requested = sources or ("prereg", "correction", "audit", "claim")
    out: list[TodoItem] = []
    for src in requested:
        if src == "prereg":
            out.extend(_prereg_todos(now=now))
        elif src == "correction":
            out.extend(_correction_todos(now=now))
        elif src == "audit":
            out.extend(_audit_todos(now=now))
        elif src == "claim":
            out.extend(_claim_todos(now=now))
    return out


def summary_counts() -> dict[str, int]:
    """Return per-source counts of action-items currently surfaced.
    Useful for the briefing-row builder that wants the headline number
    without rendering the full list."""
    return {
        "prereg": len(_prereg_todos()),
        "correction": len(_correction_todos()),
        "audit": len(_audit_todos()),
        "claim": len(_claim_todos()),
    }
