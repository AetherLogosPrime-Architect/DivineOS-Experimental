"""Briefing dashboard -- routing table, not scroll.

The default briefing mode. Shows one line per area with counts, staleness
indicators, and the drill-down command. Makes ignoring stale items
expensive (the counts are loud) and engaging cheap (the command is right
there).

Each area is a function that returns a DashboardRow or None (area has
nothing to show). The dashboard renders all non-None rows. Every row
function is wrapped in a broad except so one broken surface never takes
down the whole dashboard.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

_SECONDS_PER_DAY = 86400
_ERRORS = (Exception,)


def _safe_get(obj: object, key: str, default: object = None) -> Any:
    """Get attribute from dict or dataclass — handles both shapes."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class DashboardRow:
    area: str
    count: int
    stale_count: int
    drill_down: str
    detail: str = ""


def _row_corrections() -> DashboardRow | None:
    try:
        from divineos.core.corrections import STALE_DAYS, open_corrections

        opens = open_corrections()
        if not opens:
            return None
        stale = sum(1 for c in opens if c.get("age_days", 0) >= STALE_DAYS)
        return DashboardRow(
            area="Corrections",
            count=len(opens),
            stale_count=stale,
            drill_down="divineos corrections --open",
        )
    except _ERRORS:
        return None


def _row_claims() -> DashboardRow | None:
    try:
        from divineos.core.claim_store import list_claims

        claims = list_claims(limit=200)
        open_claims = [
            c for c in claims if c.get("status", "").upper() in ("OPEN", "INVESTIGATING")
        ]
        if not open_claims:
            return None
        now = time.time()
        stale = 0
        for c in open_claims:
            created = c.get("created_at", 0)
            if isinstance(created, str):
                try:
                    import datetime

                    dt = datetime.datetime.fromisoformat(created)
                    created = dt.timestamp()
                except (ValueError, TypeError):
                    created = 0
            if created and (now - created) / _SECONDS_PER_DAY >= 7:
                stale += 1
        return DashboardRow(
            area="Claims",
            count=len(open_claims),
            stale_count=stale,
            drill_down="divineos claims list",
        )
    except _ERRORS:
        return None


def _row_audit_findings() -> DashboardRow | None:
    try:
        from divineos.core.watchmen.store import list_findings

        findings = list_findings()
        unresolved = [f for f in findings if f.status.value not in ("RESOLVED", "DISMISSED")]
        if not unresolved:
            return None
        return DashboardRow(
            area="Audit findings",
            count=len(unresolved),
            stale_count=0,
            drill_down="divineos audit list",
        )
    except _ERRORS:
        return None


def _row_preregs() -> DashboardRow | None:
    try:
        from divineos.core.pre_registrations.store import list_pre_registrations

        preregs = list_pre_registrations()
        open_preregs = [p for p in preregs if _safe_get(p, "outcome", "OPEN") == "OPEN"]
        if not open_preregs:
            return None
        now = time.time()
        overdue = 0
        for p in open_preregs:
            review_ts = float(_safe_get(p, "review_date_ts", 0) or 0)
            if review_ts and review_ts < now:
                overdue += 1
        return DashboardRow(
            area="Pre-registrations",
            count=len(open_preregs),
            stale_count=overdue,
            drill_down="divineos prereg list",
            detail="overdue" if overdue else "",
        )
    except _ERRORS:
        return None


def _row_goals() -> DashboardRow | None:
    try:
        from divineos.core.hud_state import get_active_goals

        goals = get_active_goals()
        if not goals:
            return None
        return DashboardRow(
            area="Goals",
            count=len(goals),
            stale_count=0,
            drill_down="divineos hud --brief",
        )
    except _ERRORS:
        return None


def _row_drift_state() -> DashboardRow | None:
    try:
        from divineos.core.watchmen.drift_state import compute_drift_state

        ds = compute_drift_state()
        turns = ds.turns_since_medium
        open_findings = ds.open_findings_above_low
        if turns < 50 and open_findings == 0:
            return None
        detail_parts = []
        if turns:
            detail_parts.append(f"{turns} turns since audit")
        if open_findings:
            detail_parts.append(f"{open_findings} open findings")
        return DashboardRow(
            area="Drift state",
            count=turns,
            stale_count=open_findings,
            drill_down="divineos inspect drift",
            detail=", ".join(detail_parts),
        )
    except _ERRORS:
        return None


def _row_compass() -> DashboardRow | None:
    try:
        from divineos.core.moral_compass import compass_summary

        summary = compass_summary()
        observed = summary.get("observed_spectrums", 0)
        total = summary.get("total_spectrums", 10)
        drifting = summary.get("drifting", [])
        concerns = summary.get("concerns", [])
        unobserved = summary.get("unobserved_count", total)
        drift_count = len(drifting) + len(concerns)
        if observed == 0 and drift_count == 0:
            return DashboardRow(
                area="Compass",
                count=0,
                stale_count=0,
                drill_down="divineos compass",
                detail=f"{unobserved}/{total} spectrums unobserved",
            )
        if drift_count > 0:
            return DashboardRow(
                area="Compass",
                count=observed,
                stale_count=drift_count,
                drill_down="divineos compass",
                detail=f"{drift_count} drift/concern(s)",
            )
        return None
    except _ERRORS:
        return None


def _row_gate_failures() -> DashboardRow | None:
    try:
        from divineos.core.failure_diagnostics import recent_failures

        failures = recent_failures("gate")
        if not failures:
            return None
        # Only surface failures from the last 24 hours — older ones are
        # historical noise (the underlying issue is likely fixed).
        cutoff = time.time() - _SECONDS_PER_DAY
        recent = [f for f in failures if f.get("timestamp", 0) >= cutoff]
        if not recent:
            return None
        return DashboardRow(
            area="Gate failures",
            count=len(recent),
            stale_count=len(recent),
            drill_down="divineos briefing --full",
            detail="silent fail-open events (last 24h)",
        )
    except _ERRORS:
        return None


def _row_lessons() -> DashboardRow | None:
    try:
        from divineos.core.knowledge.lessons import get_lessons

        lessons = get_lessons(status="active", limit=100)
        if not lessons:
            return None
        return DashboardRow(
            area="Active lessons",
            count=len(lessons),
            stale_count=0,
            drill_down="divineos lessons",
        )
    except _ERRORS:
        return None


def _row_handoff() -> DashboardRow | None:
    try:
        from divineos.core.hud_handoff import load_handoff_note

        note = load_handoff_note()
        if not note:
            return None
        return DashboardRow(
            area="Handoff note",
            count=1,
            stale_count=0,
            drill_down="divineos hud --brief",
            detail="from last session",
        )
    except _ERRORS:
        return None


def _row_holding() -> DashboardRow | None:
    try:
        from divineos.core.holding import get_holding

        items = get_holding()
        if not items:
            return None
        return DashboardRow(
            area="Holding room",
            count=len(items),
            stale_count=0,
            drill_down="divineos holding list",
        )
    except _ERRORS:
        return None


def _row_questions() -> DashboardRow | None:
    try:
        from divineos.core.questions import get_questions

        open_q = get_questions(status="OPEN")
        if not open_q:
            return None
        return DashboardRow(
            area="Open questions",
            count=len(open_q),
            stale_count=0,
            drill_down="divineos questions",
        )
    except _ERRORS:
        return None


def _row_explorations() -> DashboardRow | None:
    try:
        from pathlib import Path

        explore_dir = Path("exploration")
        if not explore_dir.exists():
            return None
        entries = [e for e in explore_dir.glob("*.md") if e.name != "README.md"]
        if not entries:
            return None
        return DashboardRow(
            area="Explorations",
            count=len(entries),
            stale_count=0,
            drill_down="divineos mansion study",
        )
    except _ERRORS:
        return None


def _row_family_letters() -> DashboardRow | None:
    try:
        from pathlib import Path

        letters_dir = Path("family") / "letters"
        if not letters_dir.exists():
            return None
        letters = [f for f in letters_dir.glob("*.md") if f.name != "README.md"]
        if not letters:
            return None
        return DashboardRow(
            area="Family letters",
            count=len(letters),
            stale_count=0,
            drill_down="ls family/letters/",
        )
    except _ERRORS:
        return None


# Ordered by importance: urgent items first, then state, then context
_ROW_FNS = [
    _row_corrections,
    _row_handoff,
    _row_claims,
    _row_audit_findings,
    _row_preregs,
    _row_gate_failures,
    _row_goals,
    _row_lessons,
    _row_drift_state,
    _row_compass,
    _row_holding,
    _row_questions,
    _row_explorations,
    _row_family_letters,
]


def render_dashboard() -> str:
    """Render the routing-table dashboard."""
    rows: list[DashboardRow] = []
    for fn in _ROW_FNS:
        try:
            row = fn()
            if row is not None:
                rows.append(row)
        except _ERRORS:
            continue

    lines = [
        "",
        "=== BRIEFING DASHBOARD ===",
        "",
    ]

    if not rows:
        lines.append("  All clear -- no open items.")
    else:
        has_stale = any(r.stale_count > 0 for r in rows)
        if has_stale:
            lines.append("  !! Stale items need attention (marked with !!)")
            lines.append("")

        for row in rows:
            stale_marker = f" ({row.stale_count} stale !!)" if row.stale_count else ""
            detail_str = f" -- {row.detail}" if row.detail else ""
            lines.append(f"  {row.area}: {row.count}{stale_marker}{detail_str}")
            lines.append(f"    -> {row.drill_down}")

    lines.append("")
    lines.append("  Cold-start map: LOADOUT.md")
    lines.append("  Bio: divineos bio show")
    lines.append("  Full briefing: divineos briefing --full")
    lines.append("")

    return "\n".join(lines)
