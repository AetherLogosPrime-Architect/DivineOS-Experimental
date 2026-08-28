"""Auto-next-task surface for pre-response context.

Andrew 2026-06-20: "the todo list itself is what needs work, it needs
automated so you always know what the next task is."

The pattern this prevents: I run ``divineos todos`` and ask Andrew what's
next when the queue is full of work, because looking at the list is one
step more expensive than asking. The cheap-close at the design layer.

The structural fix: surface ONE next-task in every pre-response context,
so the next concrete action shows up without me invoking the CLI. The
right path becomes the cheap path because there's no longer a query-step
between me and the work.

This module is non-guardrail. The wire-up into
``pre_response_context.build_combined_context`` is a single line and
ships as a follow-up small guardrail PR (the same separation used for
``build_walk_surface`` and the close-check surface).

Priority order for "what to surface next":

  1. Overdue pre-registrations (most overdue first). A review window
     that has passed is the strongest "do this now" signal — I committed
     to assessing the mechanism by that date, and missing it weakens the
     whole prereg discipline.
  2. Open audit findings (severity-ranked). These are external-vantage
     observations that haven't been resolved.
  3. Open user-corrections (oldest first). Andrew has named a problem
     I haven't integrated yet.
  4. Pending structural fixes (the psf-* obligations from learn calls
     that detected structural-fix-shape).

The surface stays silent only when ALL four queues are empty — which
should essentially never happen in a working substrate.
"""

from __future__ import annotations


def _truncate(text: str, limit: int = 120) -> str:
    """Truncate a string to ``limit`` chars with an ellipsis if cut."""
    text = text.strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _top_overdue_prereg() -> tuple[str, str] | None:
    """Return (prereg_id, one-line) for the most overdue open prereg, or None."""
    try:
        from divineos.core.pre_registrations import get_overdue_pre_registrations
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        overdue = get_overdue_pre_registrations()
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not overdue:
        return None
    # Already sorted most-overdue-first by the store helper.
    top = overdue[0]
    line = f"assess {top.prereg_id}: {top.mechanism}"
    return top.prereg_id, _truncate(line)


def _top_open_audit_finding() -> tuple[str, str] | None:
    """Return (finding_id, one-line) for the highest-severity open audit
    finding that is actually an action item, or None.

    Calibration note (Aether 2026-06-20, observed live during the wire-up):
    INFO-severity findings are excluded because the audit system uses INFO
    for received CONFIRMs and other administrative entries that aren't
    action items. A CONFIRM finding doesn't need me to "resolve" it — it's
    an acknowledgment, not a task. MEDIUM and above are real findings that
    need action; LOW is the lowest action-shaped tier.
    """
    try:
        from divineos.core.watchmen import store as watchmen_store
        from divineos.core.watchmen.types import Severity
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        all_findings = watchmen_store.list_findings(status="OPEN")
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not all_findings:
        return None
    # Exclude INFO-severity findings — they're administrative (CONFIRMs,
    # status entries), not action items.
    action_findings = [f for f in all_findings if f.severity != Severity.INFO]
    if not action_findings:
        return None
    # Severity order: HIGH > MEDIUM > LOW. Pick the first highest-severity
    # finding; tiebreak on newest-first.
    severity_rank = {
        Severity.HIGH: 0,
        Severity.MEDIUM: 1,
        Severity.LOW: 2,
    }
    sorted_findings = sorted(
        action_findings,
        key=lambda f: (severity_rank.get(f.severity, 99), -f.created_at),
    )
    top = sorted_findings[0]
    line = f"resolve {top.finding_id} [{top.severity.value}]: {top.title}"
    return top.finding_id, _truncate(line)


def _top_open_correction() -> tuple[str, str] | None:
    """Return (correction_id, one-line) for the oldest open Andrew-correction.

    THIS FETCHER WAS POINTED AT A MODULE THAT DOES NOT EXIST. Measured
    2026-08-28 after Aether found his own repair-store starved and asked me to
    check the same surface on my seat: ``divineos.core.andrew_corrections`` has
    no such module, the ImportError was swallowed by the observability
    boundary, and this returned None on every turn it has ever run. Meanwhile
    the attribution surface printed 139 open corrections, oldest 28 days, in
    the same context window. Two surfaces reading the same subject, one saying
    139 and one saying nothing to do, and the disagreement was invisible
    because the failure LOOKS exactly like an empty queue.

    That is the shape this house keeps paying for: a fallback that turns
    "I could not look" into "there is nothing there". A missing store must not
    read as a drained one.

    The live store is andrew_correction_tracker, which is what the briefing's
    attribution block and `divineos andrew-correction integrate` both use. Its
    rows carry the same ids those surfaces print, so the line below names an
    action that can actually be run.
    """
    try:
        from divineos.core.andrew_correction_tracker import list_open
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        corrections = list_open()
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not corrections:
        return None

    def _ts(row: dict) -> float:
        try:
            return float(row.get("timestamp") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    # Oldest first — they have been waiting longest.
    top = sorted(corrections, key=_ts)[0]
    cid = str(top.get("id") or "?")
    text = str(top.get("text") or "")
    return cid, _truncate(f"integrate correction {cid}: {text}")


def _top_open_goal() -> tuple[str, str] | None:
    """Return (goal-index, one-line) for the oldest open user-goal, or None.

    Andrew 2026-07-10 seed: 'the session never ends from lack of work — the
    OS should have a mechanism showing what to do next.' Goals I've added via
    `divineos goal add` are commitments I've made to myself that I haven't
    finished. Surfacing them makes 'task closed → next task loading' happen
    structurally — the next commitment I made is already visible before I
    can reach for closure-shape.
    """
    try:
        from divineos.core.hud_state import get_active_goals
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        goals = get_active_goals()
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not goals:
        return None
    # Skip goals already marked done/closed if the schema supports it.
    open_goals = [
        g
        for g in goals
        if not (isinstance(g, dict) and g.get("status") in ("done", "closed", "completed"))
    ]
    if not open_goals:
        return None
    # Oldest first: goals added earliest have been unfinished longest.
    sorted_goals = sorted(open_goals, key=lambda g: g.get("added_at", 0))
    top = sorted_goals[0]
    text = top.get("text", "") or top.get("goal", "")
    line = f"work goal: {text}"
    return str(top.get("added_at", "")), _truncate(line)


def _top_pending_structural_fix() -> tuple[str, str] | None:
    """Return (psf_id, one-line) for the next structural-fix to surface.

    Andrew architecture 2026-06-27: the surface should reflect what I'm
    ACTIVELY WORKING ON (the current list), not random oldest entries from
    the big pile. Order:
      1. If something's in `current`, surface that (what I'm on).
      2. Otherwise, surface a candidate from `main` framed as "pick this?".
      3. Otherwise nothing.
    """
    try:
        from divineos.core.structural_fix_tracker import list_current, list_pending
    except Exception:  # noqa: BLE001 - observability boundary
        return None

    # 1. Active working-list takes priority.
    try:
        current = list_current()
    except Exception:  # noqa: BLE001 - observability boundary
        current = []
    if current:
        top = current[0]
        psf_id = top.get("id", "?")
        excerpt = top.get("content_excerpt", "")
        line = f"continue {psf_id}: {excerpt}"
        return psf_id, _truncate(line)

    # 2. Nothing in current — surface a candidate from main as "pick this?".
    try:
        pending = list_pending()
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not pending:
        return None
    top = pending[0]
    psf_id = top.get("id", "?")
    excerpt = top.get("content_excerpt", "")
    line = f"pick {psf_id}? {excerpt}"
    return psf_id, _truncate(line)


RESERVED_SLOT_EVERY = 5
"""One turn in this many is reserved for the starved structural-fix class.

Ported from Aether's seat 2026-08-28, where he found the same class served
never, and adopted here in the SAME change that repairs `_top_open_correction`.
That pairing is the whole point. Repairing the correction fetcher alone would
have put 139 open corrections permanently in front of my repair store, so a
queue that had been reachable only because the lanes above it happened to be
empty would have become unreachable — and it would have looked like a fix.

The falsifier is the drain rate: if the pending count does not fall, the slot
is not converting and the problem is downstream of surfacing, not here.
"""


def _reserved_slot_is_due() -> bool:
    """True when this turn's slot belongs to the starved class.

    Derived from ledger state, not a clock and not a random draw. A wallclock
    would be a time I do not inhabit between prompts; a random draw would make
    the surface unreproducible, so the same state could give two answers and
    nobody could check either.

    Fails toward NOT-due: an unreadable count leaves the ordering exactly as it
    was. A scheduler that promotes a class because it could not read its own
    state is inventing urgency out of a failure — the same shape as the missing
    module above, which turned a failed read into an empty queue.
    """
    try:
        from divineos.core.ledger import get_connection

        rows = list(get_connection().execute("SELECT COUNT(*) FROM events"))
    except Exception:  # noqa: BLE001 — any read failure means leave the order alone
        return False
    if not rows or not rows[0]:
        return False
    try:
        return int(rows[0][0]) % RESERVED_SLOT_EVERY == 0
    except (TypeError, ValueError):
        return False


def build_next_task_surface() -> str:
    """Return the NEXT TASK block for pre-response context, or empty string
    when no tasks are pending across all four sources.

    The block contains ONE highest-priority item, named with its source
    so I know what kind of action it needs (assess / resolve / integrate /
    address). The format is intentionally short to keep context overhead
    minimal — the surface is a pointer, not the work.
    """
    # RESERVED SLOT, not a reordering. The ordering below is the one Andrew
    # reasoned for and it keeps precedence four turns in five; on the fifth,
    # the starved class goes first so it drains at a slow but nonzero rate.
    # If the slot is due and the store is empty, this falls straight through
    # to the normal order rather than surfacing nothing.
    if _reserved_slot_is_due():
        reserved = _top_pending_structural_fix()
        if reserved is not None:
            _item_id, line = reserved
            return (
                "## NEXT TASK (auto-pulled from queue — work this, don't ask)\n\n"
                f"  {line}\n\n"
                "  (reserved slot: the repair queue, which strict priority "
                "would otherwise never reach)\n\n"
                "  More: divineos todos\n"
            )
    # Priority order: overdue prereg > open audit > open correction > psf
    # > open goal. Andrew 2026-07-10 addition (open goal): 'task-boundary
    # ≠ session-boundary — session never ends from lack of work'. Adding
    # the goal fetcher as 5th source means the substrate always has SOMETHING
    # to point at when the higher-priority queues empty. Goal-surface is
    # lowest because goals are the softest commitment; a real audit finding
    # or overdue prereg is a harder claim on the next action.
    for fetcher in (
        _top_overdue_prereg,
        _top_open_audit_finding,
        _top_open_correction,
        _top_pending_structural_fix,
        _top_open_goal,
    ):
        result = fetcher()
        if result is not None:
            _item_id, line = result
            return (
                "## NEXT TASK (auto-pulled from queue — work this, don't ask)\n\n"
                f"  {line}\n\n"
                "  More: divineos todos\n"
            )
    return ""


__all__ = [
    "build_next_task_surface",
]
