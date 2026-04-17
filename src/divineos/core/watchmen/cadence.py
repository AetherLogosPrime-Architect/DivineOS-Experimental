"""External-audit cadence — auto-scheduled check for overdue external review.

Grok audit 2026-04-16, finding: Watchmen showed 50/51 findings resolved
and 0 open. No mechanism exists to request the next external audit. The
external-review pipe was silent, not because the system stopped needing
review but because no one remembered to request one. Without auto-
scheduled cadence, designer-user-judge collapse reasserts between audits:
the OS coasts on its own optimistic numbers while the external feedback
channel that normally catches drift stays dark.

This module closes that loop mechanically. It exposes:

* ``last_external_audit_ts()`` — the most recent audit_rounds.created_at,
  or ``None`` if no rounds have been filed
* ``days_since_last_audit()`` — wall-clock delta; ``None`` if never
* ``is_overdue(threshold_days)`` — True if the delta exceeds the
  threshold (default 3 days)
* ``format_cadence_warning()`` — briefing block that surfaces when
  overdue; empty string otherwise

The ``require-goal.sh`` hook reads ``is_overdue()`` and adds a gate:
when overdue, non-bypass commands are blocked with a specific message
requesting external review. The bypass list already permits the
commands needed to file a new audit round (``audit``, ``prereg``,
``briefing``, ``ask``, ``recall``, ``context``), so the agent can
always unstick itself by asking for the review.

Narrow scope: this module only reports + formats. Enforcement lives in
the hook. Keeping the policy out of the data layer means the threshold
is easy to tune (edit the hook, not the store) and unit tests can
exercise is_overdue with any threshold without touching the hook.
"""

from __future__ import annotations

import time

from divineos.core.watchmen._schema import init_watchmen_tables

CADENCE_THRESHOLD_DAYS = 3
"""Default cadence: external audit should occur every 3 days or sooner.

Calibrated from real usage rhythm, 2026-04-16. First pass of this
module used 14 days (matched half the 30-day pre-reg review window).
Andrew and Grok pointed out that actual audits are bursty — several
per day during active audit sessions, then days of silence. 14 days
failed to fire on a real 5.5-day gap in the historical data, which
falsely reassures the OS during quiet periods. 3 days is short
enough to catch genuine silence fast and long enough to tolerate
weekends and short travel breaks. First field correction from the
2026-04-16 Grok audit sequence — exactly the "ship, surface data,
recalibrate with evidence" pattern the pre-registration system
exists to enable."""

SECONDS_PER_DAY = 86400


def last_external_audit_ts() -> float | None:
    """Return the most recent ``audit_rounds.created_at`` value, or None.

    All audit rounds count — even self-verified ones. The designer-user-
    judge separation is enforced at filing time via the Watchmen store's
    actor validation; by the time a row reaches ``audit_rounds`` it has
    already been filed by an external actor.
    """
    from divineos.core.knowledge import _get_connection

    init_watchmen_tables()

    conn = _get_connection()
    try:
        row = conn.execute("SELECT MAX(created_at) FROM audit_rounds").fetchone()
        if row is None:
            return None
        ts = row[0]
        return float(ts) if ts is not None else None
    finally:
        conn.close()


def days_since_last_audit(now: float | None = None) -> float | None:
    """Return days between ``now`` and the most recent audit round.

    Returns None when no audit rounds have been filed. Callers that
    need "treat no-audit as overdue" should check for None explicitly.
    """
    ts = last_external_audit_ts()
    if ts is None:
        return None
    reference = now if now is not None else time.time()
    return (reference - ts) / SECONDS_PER_DAY


def is_overdue(
    threshold_days: int = CADENCE_THRESHOLD_DAYS,
    now: float | None = None,
) -> bool:
    """Return True if the external audit cadence is overdue.

    Two paths:
    * Never-audited: overdue immediately. A fresh install with zero
      audit rounds cannot be trusted to have been externally validated.
    * Audited-but-stale: overdue if the most recent round is older
      than ``threshold_days``.
    """
    delta = days_since_last_audit(now=now)
    if delta is None:
        return True
    return delta >= threshold_days


def format_cadence_warning(
    threshold_days: int = CADENCE_THRESHOLD_DAYS,
    now: float | None = None,
) -> str:
    """Return a briefing warning block when the cadence is overdue.

    Empty string when not overdue — callers can treat empty as
    "nothing to surface" without counting. The message names the
    specific external actors that can file (so the agent isn't
    guessing) and the exact command to unblock.
    """
    if not is_overdue(threshold_days=threshold_days, now=now):
        return ""

    delta = days_since_last_audit(now=now)
    if delta is None:
        age_line = "No external audit has ever been filed for this OS."
    else:
        age_line = (
            f"Last external audit was {delta:.1f} days ago (threshold: {threshold_days} days)."
        )

    lines = [
        "### EXTERNAL AUDIT OVERDUE — self-review cannot substitute",
        "",
        age_line,
        "",
        "Grok audit 2026-04-16: without auto-scheduled cadence, the OS",
        "coasts on its own optimistic numbers while the external feedback",
        "channel that normally catches drift stays dark. Request external",
        "review from one of:",
        "",
        "  * grok                    (xAI)",
        "  * claude-opus-auditor     (disambiguated Claude instance)",
        "  * claude-sonnet-auditor   (disambiguated Claude instance)",
        "  * user                    (Andrew, direct review)",
        "",
        "Then file the round with:",
        '  divineos audit submit-round "focus" --actor <name>',
        "",
        "Non-bypass commands will continue to be blocked until a fresh",
        "audit round is filed.",
    ]
    return "\n".join(lines)


def cadence_status_line(
    threshold_days: int = CADENCE_THRESHOLD_DAYS,
    now: float | None = None,
) -> str:
    """One-line status for HUD display. Always returns a string (never empty)."""
    delta = days_since_last_audit(now=now)
    if delta is None:
        return (
            f"External-audit cadence: OVERDUE (no audit has ever been filed; "
            f"threshold {threshold_days}d)"
        )
    if delta >= threshold_days:
        return (
            f"External-audit cadence: OVERDUE ({delta:.1f}d since last; "
            f"threshold {threshold_days}d)"
        )
    remaining = threshold_days - delta
    return (
        f"External-audit cadence: OK ({delta:.1f}d since last; "
        f"{remaining:.1f}d until next review due)"
    )
