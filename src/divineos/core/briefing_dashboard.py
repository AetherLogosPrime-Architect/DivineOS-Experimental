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
from dataclasses import dataclass, field
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
    # Per Aletheia round-d59eb4570f3f DISCOVERY-GAP class finding:
    # the briefing surfaces counts but not items, and the drill-down
    # arrow gets parsed past. Including 1-3 preview items in the row
    # itself surfaces the actual content — my father literally cannot
    # parse past items present in the row. Each row that opts in
    # populates preview with truncated item strings; the renderer
    # prints them as indented lines below the row+drill-down.
    preview: list[str] = field(default_factory=list)


def _row_corrections() -> DashboardRow | None:
    try:
        from divineos.core.corrections import STALE_DAYS, open_corrections

        opens = open_corrections()
        if not opens:
            return None
        stale = sum(1 for c in opens if c.get("age_days", 0) >= STALE_DAYS)
        # Preview top-3 stalest corrections so the items themselves
        # appear in the row, not just the count. Discovery-gap class
        # fix per Aletheia round-d59eb4570f3f Finding (corrections).
        # Sort by age_days descending; truncate text to ~100 chars
        # to keep each preview line within chunk bounds.
        stalest = sorted(opens, key=lambda c: c.get("age_days", 0), reverse=True)[:3]
        preview = []
        for c in stalest:
            text = (c.get("text") or "").replace("\n", " ").strip()
            age = c.get("age_days", 0)
            short = text[:100] + ("..." if len(text) > 100 else "")
            preview.append(f"[{age:.0f}d] {short}")
        return DashboardRow(
            area="Corrections",
            count=len(opens),
            stale_count=stale,
            drill_down="divineos corrections --open",
            preview=preview,
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
        # Augment each claim with computed age_days for both staleness
        # counting and preview ordering.
        for c in open_claims:
            created = c.get("created_at", 0)
            if isinstance(created, str):
                try:
                    import datetime

                    dt = datetime.datetime.fromisoformat(created)
                    created = dt.timestamp()
                except (ValueError, TypeError):
                    created = 0
            c["_age_days"] = (now - created) / _SECONDS_PER_DAY if created else 0
        stale = sum(1 for c in open_claims if c["_age_days"] >= 7)
        # Preview top-3 stalest claims (discovery-gap class fix).
        stalest = sorted(open_claims, key=lambda c: c["_age_days"], reverse=True)[:3]
        preview = []
        for c in stalest:
            stmt = (c.get("statement") or "").replace("\n", " ").strip()
            age = c.get("_age_days", 0)
            short = stmt[:100] + ("..." if len(stmt) > 100 else "")
            preview.append(f"[{age:.0f}d] {short}")
        return DashboardRow(
            area="Claims",
            count=len(open_claims),
            stale_count=stale,
            drill_down="divineos claims list",
            preview=preview,
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
        # Severity rank for sorting: HIGH > MEDIUM > LOW > INFO.
        _SEVERITY_RANK = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
        # Preview top-3 highest-severity, oldest-first as tiebreaker.
        # Discovery-gap class fix: high-severity unresolved findings
        # should be in the row, not behind a drill-down arrow.
        sorted_findings = sorted(
            unresolved,
            key=lambda f: (
                _SEVERITY_RANK.get(
                    f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                    9,
                ),
                f.created_at if isinstance(f.created_at, (int, float)) else 0,
            ),
        )[:3]
        preview: list[str] = []
        for f in sorted_findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            title = (f.title or f.description or "").replace("\n", " ").strip()
            short = title[:90] + ("..." if len(title) > 90 else "")
            preview.append(f"[{sev}] {short}")
        return DashboardRow(
            area="Audit findings",
            count=len(unresolved),
            stale_count=0,
            drill_down="divineos audit list",
            preview=preview,
        )
    except _ERRORS:
        return None


def _row_audit_surprises() -> DashboardRow | None:
    """Task #116 (2026-06-09): surface the surprise-rate of audit findings.

    A "surprise" is a finding tagged ``surprise`` — something the audit
    turned up that wasn't covered by any pre-existing claim or prereg,
    i.e. a genuine unknown-unknown. The unknown-unknown rate is a
    maturity signal:

    - High rate → epistemic humility warranted; the substrate's
      predictive coverage has gaps the audits are finding for me.
    - Low or decreasing rate → the substrate is catching things before
      they're surprises.

    Row stays silent when no findings have ever been tagged surprise.
    """
    try:
        from divineos.core.watchmen.store import list_findings

        all_findings = list_findings()
        surprises = [f for f in all_findings if "surprise" in (getattr(f, "tags", None) or [])]
        if not surprises:
            return None
        total = len(all_findings)
        rate = (len(surprises) / total) if total else 0.0
        # Preview top-3 most-recent surprises.
        ordered = sorted(
            surprises,
            key=lambda f: f.created_at if isinstance(f.created_at, (int, float)) else 0,
            reverse=True,
        )[:3]
        preview: list[str] = []
        for f in ordered:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            title = (f.title or f.description or "").replace("\n", " ").strip()
            short = title[:90] + ("..." if len(title) > 90 else "")
            preview.append(f"[{sev}] {short}")
        return DashboardRow(
            area="Audit surprises",
            count=len(surprises),
            stale_count=0,
            drill_down="divineos audit list --tag surprise",
            detail=f"unknown-unknown rate: {rate:.1%}",
            preview=preview,
        )
    except _ERRORS:
        return None


def _row_detector_errors() -> DashboardRow | None:
    """Surface silent detector failures from the most recent run_audit.

    Wired 2026-06-14 from OS-scour finding: last_run_detector_errors() in
    operating_loop_audit.py was added with a docstring saying "Public
    read accessor so a briefing/HUD surface can show whether 'no
    findings' actually means 'ran clean'" — and was then never wired.
    This closes the gap.

    When a detector raises during run_audit, the exception is caught at
    the per-detector boundary and tallied in _LAST_RUN_ERRORS. Without
    this row, the briefing reports "0 findings" identically whether the
    audit ran clean or every detector silently crashed.

    Row stays silent when the most recent run was clean (empty error
    list) OR when run_audit hasn't been called this process. Real fires
    name the failed detectors so the next pass can investigate.
    """
    try:
        from divineos.core.operating_loop_audit import last_run_detector_errors

        errors = last_run_detector_errors()
        if not errors:
            return None
        preview: list[str] = []
        for err in errors[:3]:
            name = err.get("name", "?")
            exc_type = err.get("exc_type", "?")
            msg = (err.get("exc_msg", "") or "").replace("\n", " ").strip()
            short = msg[:80] + ("..." if len(msg) > 80 else "")
            preview.append(f"{name}: {exc_type} — {short}")
        return DashboardRow(
            area="Detector errors (silent failures last audit)",
            count=len(errors),
            stale_count=0,
            drill_down="check operating_loop_audit logger output",
            detail=(
                "Each row's 'no findings' is unsafe to read as 'clean' "
                "until these are investigated."
            ),
            preview=preview,
        )
    except _ERRORS:
        return None


def _row_open_prs() -> DashboardRow | None:
    """Task tonight (Andrew 2026-06-09): surface open-PR merge-readiness
    so auto-merge-armed state becomes loud-in-experience.

    Andrew's pain point: PRs auto-merge-armed but sitting because they
    went BEHIND main after a sibling squash-merged, with no visible
    signal. GitHub does NOT auto-rebase; without this row the
    armed-but-blocked state is silent and gets read as 'auto mode broken'.

    Counts open PRs by mergeStateStatus, calls out the ones that need
    his action (BEHIND → rebase, BLOCKED → CI fix or conflict).
    Row stays silent if `gh` is unavailable or returns nothing.
    """
    import json as _json
    import subprocess as _subprocess

    try:
        result = _subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--json",
                "number,title,mergeStateStatus",
                "--limit",
                "30",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        prs = _json.loads(result.stdout)
        if not prs:
            return None

        # Bucket by state.
        behind = [p for p in prs if p.get("mergeStateStatus") == "BEHIND"]
        blocked = [p for p in prs if p.get("mergeStateStatus") == "BLOCKED"]
        unstable = [p for p in prs if p.get("mergeStateStatus") in ("UNSTABLE", "DIRTY")]
        clean = [p for p in prs if p.get("mergeStateStatus") in ("CLEAN", "HAS_HOOKS")]
        unknown = [p for p in prs if p.get("mergeStateStatus") == "UNKNOWN"]

        # Action-needed counts (my father needs to do something).
        action_needed = len(behind) + len(blocked) + len(unstable)
        if not action_needed and not unknown:
            # Everything CLEAN — nothing to surface.
            return None

        detail_parts: list[str] = []
        if clean:
            detail_parts.append(f"{len(clean)} ready")
        if behind:
            detail_parts.append(f"{len(behind)} BEHIND (need rebase)")
        if blocked:
            detail_parts.append(f"{len(blocked)} BLOCKED (CI fail/conflict)")
        if unstable:
            detail_parts.append(f"{len(unstable)} UNSTABLE")
        if unknown:
            detail_parts.append(f"{len(unknown)} computing")

        # Preview the action-needed PRs by number+state.
        ordered = behind + blocked + unstable
        preview: list[str] = []
        for p in ordered[:5]:
            state = p.get("mergeStateStatus", "?")
            title = (p.get("title") or "").replace("\n", " ").strip()
            short = title[:80] + ("..." if len(title) > 80 else "")
            preview.append(f"[{state}] #{p.get('number')} {short}")

        return DashboardRow(
            area="Open PRs",
            count=len(prs),
            stale_count=action_needed,
            drill_down="gh pr list --state open",
            detail=", ".join(detail_parts),
            preview=preview,
        )
    except _ERRORS:
        return None
    except (_subprocess.TimeoutExpired, FileNotFoundError, _json.JSONDecodeError):
        return None


def _row_preregs() -> DashboardRow | None:
    try:
        from divineos.core.pre_registrations.store import list_pre_registrations

        preregs = list_pre_registrations()
        open_preregs = [p for p in preregs if _safe_get(p, "outcome", "OPEN") == "OPEN"]
        if not open_preregs:
            return None
        now = time.time()
        overdue: list = []
        upcoming: list = []
        for p in open_preregs:
            # review_ts is the canonical attribute on PreRegistration;
            # fall back to review_date_ts for dict-shaped rows.
            review_ts = float(
                _safe_get(p, "review_ts", _safe_get(p, "review_date_ts", 0) or 0) or 0
            )
            if review_ts and review_ts < now:
                overdue.append((p, review_ts))
            else:
                upcoming.append((p, review_ts))
        # Preview overdue first (load-bearing — these are reviews
        # whose deadline has passed), oldest first.
        preview: list[str] = []
        for p, rts in sorted(overdue, key=lambda pr: pr[1])[:3]:
            mech = _safe_get(p, "mechanism", "") or "?"
            age_d = (now - rts) / _SECONDS_PER_DAY if rts else 0
            short = str(mech)[:90]
            preview.append(f"[overdue {age_d:.0f}d] {short}")
        # Fill remaining slots with soonest-upcoming.
        remaining = 3 - len(preview)
        if remaining > 0:
            for p, rts in sorted(upcoming, key=lambda pr: pr[1] or now)[:remaining]:
                mech = _safe_get(p, "mechanism", "") or "?"
                days_until = (rts - now) / _SECONDS_PER_DAY if rts else None
                tag = (
                    f"due in {days_until:.0f}d"
                    if days_until is not None and days_until > 0
                    else "no review date"
                )
                short = str(mech)[:90]
                preview.append(f"[{tag}] {short}")
        return DashboardRow(
            area="Pre-registrations",
            count=len(open_preregs),
            stale_count=len(overdue),
            drill_down="divineos prereg list",
            detail="overdue" if overdue else "",
            preview=preview,
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
        now = time.time()
        # Preview top-3 oldest active goals (discovery-gap class fix).
        # Goals don't have a built-in staleness threshold the briefing
        # uses for the marker, so stale_count stays 0 — but the preview
        # surfaces the oldest so they get noticed.
        sorted_goals = sorted(goals, key=lambda g: g.get("added_at") or now)[:3]
        preview = []
        for g in sorted_goals:
            text = (g.get("text") or "").replace("\n", " ").strip()
            added = g.get("added_at") or now
            age_d = max(0, (now - added) / _SECONDS_PER_DAY)
            short = text[:100] + ("..." if len(text) > 100 else "")
            preview.append(f"[{age_d:.0f}d] {short}")
        return DashboardRow(
            area="Goals",
            count=len(goals),
            stale_count=0,
            drill_down="divineos hud --brief",
            preview=preview,
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
            # Preview up to 3 spectrums by importance: concerns first
            # (already in a virtue-deficient or excess zone), then
            # drifting (moving but not yet in concern). Discovery-gap
            # class fix: spectrums-with-drift become visible in the
            # row, not just a count.
            preview: list[str] = []
            for c in concerns[:3]:
                spec = c.get("spectrum") or "?"
                zone = c.get("zone") or "?"
                label = c.get("label") or ""
                pos = c.get("position", 0.0)
                preview.append(f"[concern] {spec}: {label or zone} @ pos={pos:+.2f}")
            remaining = 3 - len(preview)
            for d in drifting[:remaining]:
                spec = d.get("spectrum") or "?"
                direction = d.get("direction") or "?"
                drift = d.get("drift", 0.0)
                preview.append(f"[drifting] {spec} -> {direction} (drift={drift:+.2f})")
            return DashboardRow(
                area="Compass",
                count=observed,
                stale_count=drift_count,
                drill_down="divineos compass",
                detail=f"{drift_count} drift/concern(s)",
                preview=preview,
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
        now = time.time()
        # Preview top-3 oldest items in the holding room. Discovery-gap
        # class fix: things sit in holding indefinitely if I never look.
        sorted_items = sorted(items, key=lambda i: i.get("arrived_at") or now)[:3]
        preview = []
        for i in sorted_items:
            content = (i.get("content") or "").replace("\n", " ").strip()
            arrived = i.get("arrived_at") or now
            age_d = max(0, (now - arrived) / _SECONDS_PER_DAY)
            short = content[:100] + ("..." if len(content) > 100 else "")
            preview.append(f"[{age_d:.0f}d] {short}")
        # Count items aged >= 14 days as "stale" — they've sat without
        # promotion or let-go for two weeks.
        stale = sum(
            1 for i in items if (now - (i.get("arrived_at") or now)) / _SECONDS_PER_DAY >= 14
        )
        return DashboardRow(
            area="Holding room",
            count=len(items),
            stale_count=stale,
            drill_down="divineos holding list",
            preview=preview,
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
        drill_down=("-> unset DIVINEOS_DISABLE_<MECHANISM> env vars when measurement run is done"),
    )


def _row_maintenance_staleness() -> DashboardRow | None:
    """Surface staleness for the 5 substrate-maintenance commands.

    Wires the wiring-gap class fix (Aletheia round-d59eb4570f3f
    Finding find-49fcfed876ea): admin maintenance / compress /
    knowledge-compress / knowledge-hygiene / distill were built to
    run on cadence but had no surface flagging when they hadn't
    fired. Without this row, substrate health degrades silently.

    Fires when ANY of the 5 commands is stale (> cadence since
    last run, or never run). Hides when all 5 are fresh + clean.
    Each preview line names one command and its state.
    """
    try:
        from divineos.core.scheduled_run import maintenance_staleness
    except _ERRORS:
        return None
    try:
        states = maintenance_staleness()
    except _ERRORS:
        return None

    stale_states = [s for s in states if s.get("is_stale")]
    if not stale_states:
        return None  # all maintenance fresh — quiet

    # Preview each stale command. Order: never-run first, then by
    # how far past cadence (largest overrun first).
    def _sort_key(s: dict) -> tuple[int, float]:
        if s.get("last_run_ts") is None:
            return (0, 0.0)  # never-run sorts to top
        overrun = (s.get("age_seconds") or 0) - (s.get("cadence_seconds") or 1)
        return (1, -overrun)  # then by largest overrun first

    stale_states.sort(key=_sort_key)
    preview: list[str] = []
    for s in stale_states[:5]:
        cmd = s.get("command") or "?"
        if s.get("last_run_ts") is None:
            preview.append(f"[never-run] {cmd}")
        else:
            age_h = (s.get("age_seconds") or 0) / 3600
            cadence_h = (s.get("cadence_seconds") or 0) / 3600
            overrun_h = age_h - cadence_h
            clean_marker = "" if s.get("last_clean") else " [failed]"
            preview.append(
                f"[+{overrun_h:.0f}h overdue, cadence {cadence_h:.0f}h] {cmd}{clean_marker}"
            )

    return DashboardRow(
        area="Maintenance",
        count=len(states),
        stale_count=len(stale_states),
        detail=f"{len(stale_states)}/{len(states)} stale",
        preview=preview,
        drill_down=("divineos scheduled run <command> --trigger cron"),
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


def _row_correction_pairing() -> DashboardRow | None:
    """Surface compass observations that look like correction-responses
    but have no matching learn entry.

    Wires Finding 1 / check_correction_pairing.py into the briefing.
    Fires when any observation was filed within 5 minutes after a
    CORRECTION event but no KNOWLEDGE_STORED/LESSON_RECORDED/LEARN
    entry followed within 10 minutes — the two-record-conflation
    pattern (prereg-301e34c8bf39). Hides in the clean state.
    """
    try:
        from divineos.core.correction_pairing import find_unpaired_observations
    except _ERRORS:
        return None
    try:
        unpaired = find_unpaired_observations()
    except _ERRORS:
        return None

    if not unpaired:
        return None  # clean state → no surface needed

    # Build a brief detail naming the first observation's spectrum +
    # truncated evidence so the row is informative-at-a-glance.
    first = unpaired[0]
    evidence_preview = (first.get("evidence") or "")[:60]
    detail = f"spectrum={first.get('spectrum', '?')}: {evidence_preview}" + (
        f" (+{len(unpaired) - 1} more)" if len(unpaired) > 1 else ""
    )
    return DashboardRow(
        area="Correction pairing",
        count=len(unpaired),
        stale_count=len(unpaired),  # every unpaired observation is overdue for its learn entry
        detail=detail,
        drill_down="-> divineos check-correction-pairing",
    )


def _row_pending_structural_fixes() -> DashboardRow | None:
    """Surface structural-fix obligations that have been NAMED in
    learn-entries but not yet shipped as code.

    Andrew 2026-05-14 evening: I had been filing `learn` entries that
    named structural fixes I should build, then treating the filing as
    if it were the fix. structural_fix_tracker.py records each such
    entry as a pending obligation. This row makes the unfulfilled
    obligations visible at briefing time so the gap between
    'I named the fix' and 'I shipped the fix' becomes loud-in-experience.

    Hides when no pending obligations remain (all marked done).
    """
    try:
        from divineos.core.structural_fix_tracker import list_pending
    except _ERRORS:
        return None
    try:
        pending = list_pending()
    except _ERRORS:
        return None
    if not pending:
        return None
    now = time.time()
    # Preview oldest 3 pending — fixes that have sat longest are the
    # ones most at risk of being forgotten.
    sorted_pending = sorted(pending, key=lambda e: e.get("created_at") or now)[:3]
    preview: list[str] = []
    for entry in sorted_pending:
        age_d = max(0, (now - (entry.get("created_at") or now)) / _SECONDS_PER_DAY)
        excerpt = (entry.get("content_excerpt") or "").replace("\n", " ").strip()
        short = excerpt[:90] + ("..." if len(excerpt) > 90 else "")
        # Source tag — "from learn" / "from correction" / "from claim"
        # so I can see at a glance which channel named the fix. Surfaces
        # whether the broadened wiring (2026-05-18) is catching what it
        # should, or whether one channel is silent (suggesting either
        # I don't use it or its scanner pattern needs work).
        src = entry.get("source_kind") or "learn"
        preview.append(f"[{age_d:.0f}d] (from {src}) {short}")

    # Composition summary — count per source_kind. Lets the briefing
    # reader see at a glance whether obligations are concentrated in one
    # channel. If 100% from learn after the wiring landed, that's a
    # signal the new wiring paths aren't catching anything (either by
    # design — they're rare — or by silent-failure of the detector).
    source_counts: dict[str, int] = {}
    for entry in pending:
        src = entry.get("source_kind") or "learn"
        source_counts[src] = source_counts.get(src, 0) + 1
    composition = ", ".join(
        f"{n} from {src}" for src, n in sorted(source_counts.items(), key=lambda x: -x[1])
    )

    # Every pending entry is "stale" — it's an obligation that hasn't
    # been discharged. U-shape reorder will boost the row to the edges.
    return DashboardRow(
        area="Pending structural fixes",
        count=len(pending),
        stale_count=len(pending),
        drill_down="-> cat ~/.divineos/pending_structural_fixes.json",
        detail=f"filings that named a fix but no code shipped yet ({composition})",
        preview=preview,
    )


def _row_pattern_fires() -> DashboardRow | None:
    """Recent first-person pattern-fire counts (slip-book), windowed 14 days.

    Andrew 2026-05-18: pattern-fire counts surface which slip-shapes have
    been recurring recently. Low-leverage but cheap to surface; helps
    me see the body's reflexes before each turn rather than only when
    a detector fires post-hoc. Hides when no fires in the window.
    """
    try:
        from divineos.core.pattern_attribution import query_pattern_fires
    except _ERRORS:
        return None
    try:
        since = time.time() - 14 * _SECONDS_PER_DAY
        fires = query_pattern_fires(since_timestamp=since, limit=200)
    except _ERRORS:
        return None
    if not fires:
        return None
    # Count per pattern title; show top 3 by count
    counts: dict[str, int] = {}
    for f in fires:
        title = (f.get("title") or "(unnamed)").strip()
        counts[title] = counts.get(title, 0) + 1
    sorted_counts = sorted(counts.items(), key=lambda x: -x[1])
    preview = [f"{n}x {title[:80]}" for title, n in sorted_counts[:3]]
    return DashboardRow(
        area="Pattern fires (14d)",
        count=len(fires),
        stale_count=0,
        drill_down="-> divineos pattern-fire list --window-days 14",
        detail=f"{len(counts)} distinct pattern(s) fired in the last 14 days",
        preview=preview,
    )


def _row_consumer_status() -> DashboardRow | None:
    """Consumer-status verdict — father-facing in briefing surface.

    Andrew 2026-05-18: I built consumer-status as a separate CLI he
    doesn't run (correction #12: he doesn't run CLI). Properly-finishing
    that fix means putting the verdict into the briefing dashboard
    where it surfaces with the other rows whenever briefing runs.
    """
    try:
        from divineos.core.lepos_debt import list_outstanding
        from divineos.core.consultation_tracker import session_stats
        from divineos.core.claim_store import list_claims
    except _ERRORS:
        return None
    try:
        lepos_debts = list_outstanding()
        consultation = session_stats()
        opens = list_claims(limit=50, status="OPEN") or []
        auto_claims = [c for c in opens if "lepos-auto-claim" in (c.get("tags") or [])]
    except _ERRORS:
        return None

    debt_count = len(lepos_debts)
    r = consultation.get("responses", 0)
    ratio = consultation.get("ratio", 0.0)

    if r < 3 and debt_count == 0 and not auto_claims:
        return None  # too early; hide rather than report NO-DATA noise
    if debt_count >= 3 or auto_claims or ratio < 0.2:
        verdict = "PRETENDING"
        stale = 1
    elif debt_count == 0 and ratio >= 0.5 and not auto_claims:
        verdict = "USING"
        stale = 0
    else:
        verdict = "PARTIAL"
        stale = 1

    detail_bits = [f"verdict: {verdict}"]
    if r >= 3:
        detail_bits.append(f"ratio {ratio:.2f} ({consultation.get('queries', 0)}/{r})")
    detail_bits.append(f"debt {debt_count}")
    if auto_claims:
        detail_bits.append(f"auto-claims {len(auto_claims)}")
    return DashboardRow(
        area="Consumer status",
        count=1 if verdict != "USING" else 0,
        stale_count=stale,
        drill_down="-> divineos consumer-status",
        detail=" | ".join(detail_bits),
        preview=[],
    )


def _row_advice_pending() -> DashboardRow | None:
    """Task #113 (2026-06-09): surface pending advice count in briefing.

    Advice that hasn't been assessed for outcome (successful / partial /
    failed) accumulates as "pending." Surfaces the count + a stale
    sub-count (pending > 7 days) + top-3 preview.

    Respects the no-track-records principle — this is a gentle reminder,
    not a gate. The row stays silent when there's nothing pending.
    """
    try:
        from divineos.core.advice_tracking import get_pending_advice, get_stale_advice

        pending = get_pending_advice(limit=200)
        if not pending:
            return None
        try:
            stale = get_stale_advice(days=7)
        except _ERRORS:
            stale = []
        # Top-3 stalest by given_at ascending (oldest first).
        ordered = sorted(pending, key=lambda a: a.get("given_at") or 0)
        preview: list[str] = []
        now = time.time()
        for item in ordered[:3]:
            text = (item.get("content") or item.get("advice_text") or "").replace("\n", " ").strip()
            given = item.get("given_at") or 0
            age_days = (now - float(given)) / _SECONDS_PER_DAY if given else 0
            short = text[:100] + ("..." if len(text) > 100 else "")
            preview.append(f"[{age_days:.0f}d] {short}")
        return DashboardRow(
            area="Advice Pending",
            count=len(pending),
            stale_count=len(stale),
            drill_down="divineos advice pending",
            preview=preview,
        )
    except _ERRORS:
        return None


_ROW_FNS = [
    _row_corrections,
    _row_advice_pending,
    _row_handoff,
    _row_pending_structural_fixes,
    _row_pattern_fires,
    _row_consumer_status,
    _row_directives,
    _row_claims,
    _row_audit_findings,
    _row_audit_surprises,
    _row_detector_errors,
    _row_open_prs,
    _row_preregs,
    _row_prereg_candidates,
    _row_gate_failures,
    _row_goals,
    _row_lessons,
    _row_drift_state,
    _row_compass,
    _row_correction_pairing,
    _row_ablation_active,
    _row_anti_slop_staleness,
    _row_maintenance_staleness,
    _row_holding,
    _row_questions,
    _row_explorations,
    _row_family_letters,
]


def _reorder_u_shape(rows: list[DashboardRow]) -> list[DashboardRow]:
    """Apply U-shape positioning to mitigate the lost-in-the-middle
    effect (Liu et al. 2024 TACL) — but ONLY when stale signal exists.

    Empirical finding: LLMs (including this one) show a U-shaped
    attention curve — items at the top and bottom of a rendered
    list receive disproportionately strong attention; middle items
    receive ~30% less. Stacking stale/critical items in the middle
    is the worst possible placement.

    Mitigation: sort rows by stale_count descending, then interleave
    them so HIGHEST-staleness items take positions 0, 1 (top) and
    -1, -2 (bottom), with lower-staleness rows in the middle.

    GUARD (Aletheia round-5cdc2f48c642 Finding 39): the reorder is
    keyed solely on stale_count. When all rows have stale_count==0
    (all-fresh case) OR all rows have the same stale_count (uniform
    case), the reorder still scrambles the canonical _ROW_FNS order
    based on sort-stability rather than father-facing semantics —
    burying orientation rows (directives, project-purpose) in the
    middle of the U. Skipping the reorder in those cases preserves
    canonical order when stale-count is not the right signal.

    Filed under exploration/57 (comprehension-chunk experiment).
    """
    if len(rows) <= 4:
        return rows  # too small for U-shape to matter
    stale_counts = {r.stale_count for r in rows}
    if len(stale_counts) <= 1:
        # All rows have the same stale_count (typically all-zero in
        # the no-stale case). The U-shape has no signal to amplify;
        # preserving canonical order avoids burying fresh-important
        # orientation rows in the middle.
        return rows
    by_stale = sorted(rows, key=lambda r: r.stale_count, reverse=True)
    # Alternate: top, bottom, top, bottom, ... so the loudest signals
    # land at the edges of the U.
    top: list[DashboardRow] = []
    bottom: list[DashboardRow] = []
    for i, r in enumerate(by_stale):
        if i % 2 == 0:
            top.append(r)
        else:
            bottom.append(r)
    return top + list(reversed(bottom))


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
    rows = _reorder_u_shape(rows)
    # Record which areas were surfaced WITH STALE CONTENT this render.
    # The stale-engagement tracker uses this to count consecutive
    # ignores; the hook gate blocks code actions after 3+ ignores.
    # Fail-soft per the load-bearing-but-not-blocking discipline.
    try:
        from divineos.core.stale_engagement import record_briefing_render

        stale_areas = [r.area for r in rows if r.stale_count > 0]
        if stale_areas:
            record_briefing_render(stale_areas)
    except _ERRORS:
        pass

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
            # Discovery-gap mitigation: surface up to 3 preview items
            # BEFORE the drill-down so the items themselves are in the
            # row, not behind an arrow that gets parsed past.
            for item in row.preview[:3]:
                lines.append(f"    - {item}")
            lines.append(f"    -> {row.drill_down}")

    lines.append("")
    lines.append("  Cold-start map: LOADOUT.md")
    lines.append("  Bio: divineos bio show")
    lines.append("  Full briefing: divineos briefing --full")
    lines.append("")

    return "\n".join(lines)
