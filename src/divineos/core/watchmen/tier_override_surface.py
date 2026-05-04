"""Briefing surface for recent TIER_OVERRIDE events.

Closes the partial-theater finding originally surfaced by a Schneier-
lens walk (the original walk write-up was a private exploration entry
that didn't survive the gitignore — audit finding 2026-05-03 round 8
flagged the stranded reference). The finding it produced, in plain
language: the TIER_OVERRIDE event system shipped earlier (commit
f08fd2a) makes every tier override auditable in the ledger — but
"loud in ledger" is not "loud in experience" if no one reads the
ledger. Briefing must surface recent overrides so the audit trail
becomes actionable at session start.

The full Schneier walk produced four findings (Sch1–Sch4); only Sch2
(this surface) and Sch3 (drift_state) shipped. Sch1 and Sch4 are open
audit-substrate work, tracked separately.

Pattern mirrors ``corrections.format_for_briefing``,
``presence_memory.format_for_briefing``, and
``watchmen.drift_state.format_for_briefing``: a plain formatter that
emits a named block when there is something to surface.
"""

from __future__ import annotations

import json
import sqlite3
import time

TIER_OVERRIDE_EVENT_TYPE = "TIER_OVERRIDE"


def recent_tier_overrides(limit: int = 5, since_days: float = 7.0) -> list[dict]:
    """Return recent TIER_OVERRIDE events, newest-first.

    Default window of 7 days matches the briefing cadence for other
    audit-related surfaces. Events older than the window are filed but
    not surfaced — reading the full history is via
    ``divineos search TIER_OVERRIDE`` for forensic review.
    """
    from divineos.core._ledger_base import get_connection

    cutoff = time.time() - (since_days * 86400.0)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, actor, payload FROM system_events "
            "WHERE event_type = ? AND timestamp > ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (TIER_OVERRIDE_EVENT_TYPE, cutoff, limit),
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

    results: list[dict] = []
    for ts, actor, payload_json in rows:
        try:
            payload = json.loads(payload_json) if isinstance(payload_json, str) else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        results.append(
            {
                "timestamp": ts,
                "actor": actor,
                "round_id": payload.get("round_id", "?"),
                "from_tier": payload.get("from_tier", "?"),
                "to_tier": payload.get("to_tier", "?"),
                "focus_preview": payload.get("focus_preview", ""),
            }
        )
    return results


def format_for_briefing(limit: int = 5, since_days: float = 7.0) -> str:
    """Return a briefing block surfacing recent tier overrides.

    Empty string when there are no overrides in the window — briefings
    stay quiet unless there's something to report. When overrides
    exist, each one is named with actor, tier delta, and focus preview
    so the operator can decide at a glance whether the override was
    legitimate.
    """
    overrides = recent_tier_overrides(limit=limit, since_days=since_days)
    if not overrides:
        return ""

    lines = [
        f"[tier overrides] {len(overrides)} in last {int(since_days)}d — "
        "every override bypasses the actor-default tier; verify legitimacy:",
    ]
    for ov in overrides:
        round_short = str(ov["round_id"])[:16]
        focus_short = str(ov["focus_preview"])[:60]
        lines.append(
            f"  - {ov['actor']}: {ov['from_tier']} -> {ov['to_tier']} "
            f"({round_short}) — {focus_short}"
        )
    lines.append("  Full forensic view: divineos search TIER_OVERRIDE")
    return "\n".join(lines) + "\n"


__all__ = [
    "TIER_OVERRIDE_EVENT_TYPE",
    "format_for_briefing",
    "recent_tier_overrides",
]
