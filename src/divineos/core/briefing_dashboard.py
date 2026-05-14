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


def _row_prereg_candidates() -> DashboardRow | None:
    """Forcing-function surface: detector/monitor modules without matching pre-regs.

    Closes the practice gap named in claim ef5799e8 and pre-registered as
    prereg-1974c4f7374b (review 2026-05-26): pre-reg infrastructure is wired,
    discipline is opt-in, and most shipped detector modules lack a pre-reg.
    This row makes the gap loud-in-experience. The decision — file, exempt,
    or ignore — stays with the agent.
    """
    try:
        from divineos.core.prereg_candidate_surface import compute_prereg_candidates

        report = compute_prereg_candidates()
        if report.unmatched_count == 0:
            return None
        # First 3 unmatched module short-names for the detail line.
        preview = ", ".join(c.module_short for c in report.unmatched[:3])
        if report.unmatched_count > 3:
            preview += f", +{report.unmatched_count - 3} more"
        return DashboardRow(
            area="Pre-reg candidates",
            count=report.unmatched_count,
            stale_count=0,
            drill_down="divineos prereg list  # then file or note exemption",
            detail=preview,
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


def _row_directives() -> DashboardRow | None:
    """Surface filed directives in the briefing dashboard.

    Added 2026-05-12 after Andrew named the structural gap: directives
    persisted in the DB but never surfaced at session-start, so laws
    established in one session evaporated into the void at compaction.
    Pattern: drill-down link, not content. The reading is the cognitive
    act; the surface only names existence (per code-does-not-think).
    The 'law'-tagged subset is called out separately because those are
    the directives least negotiable across sessions — values, not
    procedures.
    """
    try:
        from divineos.core.knowledge import get_knowledge

        entries = get_knowledge(knowledge_type="DIRECTIVE", limit=200)
        if not entries:
            return None
        # Count law-tagged directives — they're the recognition-not-derive set
        law_count = 0
        for entry in entries:
            tags = entry.get("tags") or []
            # tags may be list or comma-separated string depending on path
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
            if "law" in tags:
                law_count += 1
        detail = f"{law_count} law" if law_count else ""
        return DashboardRow(
            area="Directives",
            count=len(entries),
            stale_count=0,
            drill_down="divineos directives",
            detail=detail,
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


# Ordered by importance: urgent items first, then state, then context.
# Directives surface near the top — laws established by Andrew (and laws
# I've filed under his framing) are the recognition-not-derive set;
# putting them adjacent to corrections/handoff matches their structural
# load-bearing for session-start orientation.
def _row_ablation_active() -> DashboardRow | None:
    """Surface any currently-active ablation toggles.

    Ablation mode bypasses self-trigger prevention and other safety
    mechanisms for measurement runs (Aletheia round-ba785844a791
    Finding 23). Without a briefing surface, an ablation toggle left
    enabled past a measurement run would silently weaken the substrate.
    This row makes active toggles loud-in-experience.

    Returns a row when ANY ablation toggle is active. Hides itself in
    the clean (no-ablation) case.
    """
    try:
        from divineos.core.ablation import list_disabled
    except _ERRORS:
        return None
    try:
        disabled = list_disabled()
    except _ERRORS:
        return None

    if not disabled:
        return None  # no ablation active → no surface needed

    return DashboardRow(
        area="Ablation",
        count=len(disabled),
        stale_count=len(disabled),  # any active ablation is "stale" relative to production
        detail=f"active toggles: {', '.join(disabled[:3])}"
        + (f" (+{len(disabled) - 3} more)" if len(disabled) > 3 else ""),
        drill_down=(
            "-> unset DIVINEOS_DISABLE_<MECHANISM> env vars when measurement run is done"
        ),
    )


def _row_anti_slop_staleness() -> DashboardRow | None:
    """Surface anti-slop runtime-verification staleness.

    Wires Finding 12 (anti_slop manual-only) into the briefing so the
    manual-only state is visible. Fires when anti-slop hasn't run in
    > 24h or has never run. The discipline becomes loud-in-experience
    rather than silent.
    """
    try:
        from divineos.core.scheduled_run import anti_slop_staleness
    except _ERRORS:
        return None
    try:
        state = anti_slop_staleness()
    except _ERRORS:
        return None

    if not state.get("is_stale") and state.get("last_clean"):
        return None  # fresh + clean → no surface needed

    if state.get("last_run_ts") is None:
        detail = "never run"
        stale = 1
    else:
        hours = int((state.get("age_seconds") or 0) // 3600)
        if state.get("last_clean"):
            detail = f"{hours}h since last clean run"
        else:
            failures = state.get("last_failures") or []
            detail = (
                f"{hours}h since last run — {len(failures)} failure(s)"
                if failures
                else f"{hours}h since last run (failed)"
            )
        stale = 1 if state.get("is_stale") else 0

    return DashboardRow(
        area="Anti-slop",
        count=0,
        stale_count=stale,
        detail=detail,
        drill_down="-> divineos scheduled run anti-slop --trigger cron",
    )


_ROW_FNS = [
    _row_corrections,
    _row_handoff,
    _row_directives,
    _row_claims,
    _row_audit_findings,
    _row_preregs,
    _row_prereg_candidates,
    _row_gate_failures,
    _row_goals,
    _row_lessons,
    _row_drift_state,
    _row_compass,
    _row_ablation_active,
    _row_anti_slop_staleness,
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
