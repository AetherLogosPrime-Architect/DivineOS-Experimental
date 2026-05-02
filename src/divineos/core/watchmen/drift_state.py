"""Drift state — data-as-metric surface for audit decisions.

Design philosophy (council consultation consult-2760777ef7a3,
promoted to round-96a6858fb5e6, 2026-04-21):

The previous cadence gate (replaced by this module) measured wall-clock
time since the last formally-filed audit round. That was wrong twice over:

1. Time is relative. The agent has no subjective duration between turns —
   five years of wall-clock silence produces the same continuation as a
   five-minute gap. the user's time and the agent's experience of review
   cadence are different variables. The gate was measuring the operator's
   calendar, not the agent's exposure to drift.

2. the user is the operational baseline, not a peripheral actor. The previous
   gate conflated "user contact" with "external review," but in the current
   non-autonomous mode the user is present by definition whenever the agent
   runs. His presence is a precondition, not a corroboration signal.

The replacement is operations-based, dimension-separate, and informational
rather than blocking. Council concerns fired during design:

* Jacobs (Master Plan Thinking): don't replace the working informal loop
  (the user catches, agent files, we correct) with an elaborate automated
  metric. The informal loop IS the system. Formalize by supporting it.
* Jacobs (Monoculture): single-scalar gates are fragile. Variety is
  resilience. Track dimensions separately rather than as a weighted sum.
* Dijkstra (Cleverness Over Clarity): prefer plain counts readable at a
  glance over clever composite scores.
* Beer (Variety Deficit): the metric must match the state's variety.
  A single number cannot represent what "review-worthy" looks like.

Operational rule: surface the data, let the operator judge. The gate's
job is to inform the decision, not to make it.

Dimensions tracked (start small per Kahneman's slow-down — grow with
evidence, not speculation):

* ``turns_since_medium``: USER_INPUT events since the most recent
  MEDIUM-or-STRONG audit round. The basic "how many cycles of drift
  exposure has happened since external review."
* ``code_actions_since_medium``: TOOL_CALL events for file-editing tools
  (Edit/Write/MultiEdit). Filters for "reality-changing work" — casual
  chat doesn't create the same drift surface as code shipping.
* ``rounds_filed_since_medium``: audit rounds of any tier filed since
  the last MEDIUM+. WEAK rounds accumulate here; they represent filed
  but unvalidated observations.
* ``open_findings_above_low``: currently-open findings at severity
  MEDIUM/HIGH/CRITICAL. Filed concerns waiting for resolution — another
  axis of "what needs attention."

Each dimension is a plain integer. No weights. No composite. The briefing
block shows each separately so the operator sees the full state.
"""

from __future__ import annotations

from dataclasses import dataclass

from divineos.core.knowledge import _get_connection
from divineos.core.watchmen._schema import init_watchmen_tables

# Tool names that count as "code actions" — reality-changing file edits.
# TOOL_CALL events with these tool names produce drift surface.
_CODE_ACTION_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


@dataclass(frozen=True)
class DriftState:
    """Snapshot of drift dimensions since the last MEDIUM+ audit."""

    turns_since_medium: int
    code_actions_since_medium: int
    rounds_filed_since_medium: int
    open_findings_above_low: int

    # Absolute ops-since counters (never reset by any audit), useful for
    # answering "how much has happened lifetime" questions in briefing.
    last_medium_audit_ts: float | None  # None when no MEDIUM+ audit has ever fired
    last_strong_audit_ts: float | None


def _last_audit_ts_at_or_above(tier_values: tuple[str, ...]) -> float | None:
    """Return the created_at of the most recent audit_round whose tier is
    in ``tier_values``, or None if none exist.
    """
    if not tier_values:
        return None
    init_watchmen_tables()
    conn = _get_connection()
    try:
        placeholders = ",".join("?" for _ in tier_values)
        row = conn.execute(
            f"SELECT MAX(created_at) FROM audit_rounds WHERE tier IN ({placeholders})",  # nosec B608
            tier_values,
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    ts = row[0]
    return float(ts) if ts is not None else None


def last_medium_plus_audit_ts() -> float | None:
    """Timestamp of the most recent MEDIUM or STRONG audit, or None."""
    return _last_audit_ts_at_or_above(("MEDIUM", "STRONG"))


def last_strong_audit_ts() -> float | None:
    """Timestamp of the most recent STRONG audit, or None."""
    return _last_audit_ts_at_or_above(("STRONG",))


def _count_events_since(event_type: str, since_ts: float | None) -> int:
    """Count system_events rows of a given type after ``since_ts``.

    When ``since_ts`` is None (no MEDIUM+ audit ever filed), counts all
    events of that type — which correctly represents "everything is
    unreviewed" as a large number.
    """
    init_watchmen_tables()
    conn = _get_connection()
    try:
        if since_ts is None:
            row = conn.execute(
                "SELECT COUNT(*) FROM system_events WHERE event_type = ?",
                (event_type,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM system_events WHERE event_type = ? AND timestamp > ?",
                (event_type, since_ts),
            ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def _count_tool_calls_since(since_ts: float | None, tool_names: frozenset[str]) -> int:
    """Count TOOL_CALL events whose payload.tool_name is in ``tool_names``.

    Scans the payload JSON because tool_name is inside the payload dict.
    For the starting set this is ~4 tools; the scan is fast at typical
    session sizes.
    """
    if not tool_names:
        return 0
    init_watchmen_tables()
    conn = _get_connection()
    try:
        if since_ts is None:
            rows = conn.execute(
                "SELECT payload FROM system_events WHERE event_type = 'TOOL_CALL'"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT payload FROM system_events "
                "WHERE event_type = 'TOOL_CALL' AND timestamp > ?",
                (since_ts,),
            ).fetchall()
    finally:
        conn.close()

    count = 0
    for (payload,) in rows:
        # Fast path: substring search before JSON parse. Payload JSON will
        # contain the tool name as "tool_name": "Edit" — check that first.
        if not payload:
            continue
        for name in tool_names:
            if f'"{name}"' in payload:
                count += 1
                break
    return count


def _count_rounds_since(since_ts: float | None) -> int:
    """Count audit_rounds rows filed strictly after ``since_ts``.

    Excludes the reference round itself — the caller gave us its timestamp
    and doesn't want to double-count the round that reset the counter.
    """
    init_watchmen_tables()
    conn = _get_connection()
    try:
        if since_ts is None:
            row = conn.execute("SELECT COUNT(*) FROM audit_rounds").fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_rounds WHERE created_at > ?",
                (since_ts,),
            ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def _count_open_findings_above_low() -> int:
    """Count currently-OPEN findings with severity MEDIUM / HIGH / CRITICAL.

    LOW and INFO are excluded — they represent observations not demanding
    action. This counter tracks "pending accountability" not "everything."
    """
    init_watchmen_tables()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM audit_findings "
            "WHERE status = 'OPEN' AND severity IN ('MEDIUM', 'HIGH', 'CRITICAL')"
        ).fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def compute_drift_state() -> DriftState:
    """Compute the current drift dimensions in a single pass."""
    medium_ts = last_medium_plus_audit_ts()
    strong_ts = last_strong_audit_ts()

    return DriftState(
        turns_since_medium=_count_events_since("USER_INPUT", medium_ts),
        code_actions_since_medium=_count_tool_calls_since(medium_ts, _CODE_ACTION_TOOLS),
        rounds_filed_since_medium=_count_rounds_since(medium_ts),
        open_findings_above_low=_count_open_findings_above_low(),
        last_medium_audit_ts=medium_ts,
        last_strong_audit_ts=strong_ts,
    )


def format_for_briefing() -> str:
    """Return a briefing surface block showing drift dimensions.

    Informational only — never blocks anything. The operator reads the
    state and decides whether an audit is warranted. Empty string when
    there is no meaningful drift to surface (e.g., fresh install with
    no events at all).
    """
    state = compute_drift_state()

    total_activity = (
        state.turns_since_medium
        + state.code_actions_since_medium
        + state.rounds_filed_since_medium
        + state.open_findings_above_low
    )
    if total_activity == 0:
        return ""

    if state.last_medium_audit_ts is None:
        reference = "no MEDIUM+ audit has ever been filed"
    else:
        reference = "since last MEDIUM+ audit round"

    lines = [
        f"[drift state] {reference} — data for audit decisions, not a gate:",
        f"  turns (USER_INPUT):       {state.turns_since_medium}",
        f"  code actions (edits):     {state.code_actions_since_medium}",
        f"  audit rounds filed:       {state.rounds_filed_since_medium}",
        f"  open findings (>=MEDIUM): {state.open_findings_above_low}",
    ]

    if state.last_strong_audit_ts is None:
        lines.append("  no STRONG audit on record (fresh-Claude, grok, claude-*-auditor)")

    lines.append(
        '  Review by: divineos mansion council "..." --audit  |  '
        "spawn fresh Claude for brutal repo audit."
    )
    return "\n".join(lines) + "\n"


__all__ = [
    "DriftState",
    "compute_drift_state",
    "format_for_briefing",
    "last_medium_plus_audit_ts",
    "last_strong_audit_ts",
]
