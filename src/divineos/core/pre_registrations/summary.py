"""Pre-registration summary helpers — formatting for HUD and CLI.

The briefing integration is the load-bearing part: overdue pre-registrations
must surface prominently so a mechanism's scheduled review cannot silently
pass. Formatted here (so callers don't re-implement), consumed by hud.py.
"""

from __future__ import annotations

import time

from divineos.core.pre_registrations.store import (
    count_by_outcome,
    get_overdue_pre_registrations,
    list_pre_registrations,
)
from divineos.core.pre_registrations.types import Outcome


def format_overdue_warning() -> str:
    """Return a briefing-top warning block for overdue pre-registrations.

    Returns an empty string if none are overdue. Callers can treat empty as
    "nothing to surface" without needing to count.
    """
    overdue = get_overdue_pre_registrations()
    if not overdue:
        return ""

    now = time.time()
    lines = [
        f"### PRE-REGISTRATIONS OVERDUE ({len(overdue)}) — review required",
        "",
        "These predictions scheduled a review date that has passed. A mechanism",
        "whose review is overdue cannot be trusted to still be doing what it",
        "claimed without reconciliation. Run the review, record an outcome,",
        "or file a DEFERRED outcome with a new review date.",
        "",
    ]
    for p in overdue[:10]:
        days_overdue = (now - p.review_ts) / 86400
        lines.append(
            f"  [{p.prereg_id}] {p.mechanism}: {p.claim[:80]}"
            + (" ..." if len(p.claim) > 80 else "")
        )
        lines.append(
            f"    review was {days_overdue:.1f}d ago  |  "
            f"falsifier: {p.falsifier[:90]}" + (" ..." if len(p.falsifier) > 90 else "")
        )
    if len(overdue) > 10:
        lines.append(f"  ... and {len(overdue) - 10} more")

    lines.append("")
    lines.append("Run: divineos prereg overdue")
    return "\n".join(lines)


def prereg_loop_status() -> str:
    """Honest label for how much of the pre-registration loop is closed.

    Updated manually. The goal of pre-registrations is Goodhart prevention:
    every detector ships with a falsifier and a scheduled review, so numbers
    can't quietly drift up while habits don't change. This label describes
    whether that mechanism is active end-to-end or partial.
    """
    return (
        "Loop status: filing + overdue-surfacing + one-way outcome = wired. "
        "Briefing top-slot surfaces overdue reviews. Outcomes require an "
        "external actor. Review dates fire independent of agent memory. "
        "The loop is only fully closed once a review produces an outcome AND "
        "that outcome alters downstream behavior — which is what we're "
        "measuring over the next 30-60 days."
    )


def format_summary() -> str:
    """Return a plain-text summary of pre-registration state by outcome."""
    counts = count_by_outcome()
    total = sum(counts.values())
    open_count = counts.get(Outcome.OPEN.value, 0)
    overdue = len(get_overdue_pre_registrations())

    lines = [
        "=== Pre-registrations ===",
        "",
        prereg_loop_status(),
        "",
        f"  Total:      {total}",
        f"  Open:       {open_count} ({overdue} overdue)",
        f"  Success:    {counts.get(Outcome.SUCCESS.value, 0)}",
        f"  Failed:     {counts.get(Outcome.FAILED.value, 0)}",
        f"  Inconclusive: {counts.get(Outcome.INCONCLUSIVE.value, 0)}",
        f"  Deferred:   {counts.get(Outcome.DEFERRED.value, 0)}",
    ]

    if total == 0:
        lines.append("")
        lines.append("  No pre-registrations filed yet. Any new detector, mechanism,")
        lines.append("  or instrumentation claim should ship with a pre-registration")
        lines.append("  that names its falsifier and schedules its review.")
        return "\n".join(lines)

    # Show most recent few as context
    recent = list_pre_registrations(limit=5)
    if recent:
        lines.append("")
        lines.append("  Most recent:")
        for p in recent:
            lines.append(f"    [{p.outcome.value:12}] {p.mechanism}: {p.claim[:60]}")

    return "\n".join(lines)
