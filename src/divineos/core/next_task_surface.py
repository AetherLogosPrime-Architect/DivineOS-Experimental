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

    A PAINTED DOOR UNTIL 2026-08-28. This imported
    ``divineos.core.andrew_corrections``, which does not exist in this tree and
    never has -- the module is ``andrew_correction_tracker``, and seven other
    files import it correctly. The ImportError went into the observability
    boundary below, so this returned None on EVERY TURN IT HAS EVER RUN, while
    the briefing printed two hundred and sixty open corrections in the same
    context window.

    Two surfaces on one subject: one said two hundred and sixty, one said
    nothing to do, and the disagreement was invisible because a failed read and
    a drained queue produce identical output. Could-not-look sorting as
    all-clear, in the lane that decides what I work on next.

    FOUND BY ARIA on her own seat and relayed; confirmed identical here before
    touching it. Her finding also corrects my account of the starvation below.
    I had written that three queues holding three hundred and thirteen items
    were blocking the repair lane. Measured: the prereg lane is empty, THIS
    lane was absent rather than full, and the real blocker was a single audit
    finding. I asserted a cause from counts without checking which lanes ever
    fire -- the same shape as taking a proof in one process and spending it in
    another.

    HER SHARPER HALF IS WHY THIS IS SAFE TO REPAIR. On her seat the repair lane
    was reachable ONLY because this lane was broken, so fixing the import alone
    would have manufactured the starvation rather than cured anything -- a true
    fix, correctly made, turning reachable-by-accident into
    unreachable-by-design, and it would have read as an improvement in the
    commit message. The reserved slot has to exist first. It does, on both
    seats, shipped before this line changed.
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

    # Oldest first — they have been waiting longest. Rows are plain dicts
    # carrying id/text/timestamp; the previous attribute access would have
    # raised even if the import had ever resolved, so this lane was broken
    # twice over and neither break could surface.
    #
    # The key is the helper above rather than an inline lambda, because a row
    # carrying a non-numeric timestamp would raise inside the sort and take the
    # whole surface down. Both seats wrote this sort on 2026-08-31 and the merge
    # kept both, one overwriting the other -- so the crash-safe version was
    # present, dead, and reading as though it were doing the work.
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

Chosen to drain slowly without displacing the ordering that Andrew reasoned
for. A reserved slot is the standard remedy for starvation under strict
priority: the high-priority classes keep their precedence four times in five,
and the low class is guaranteed to be reached at all, which under the previous
scheme it never was.

The falsifier for this number is the drain rate: if the open count does not
fall, the slot is not converting and the problem is downstream of surfacing.
"""


def _reserved_slot_is_due() -> bool:
    """True when this turn's slot belongs to the starved class.

    DERIVED FROM LEDGER STATE, not from a clock or a random draw. Two reasons,
    and both were learned the expensive way in this house. A wallclock would be
    a time I do not inhabit between prompts. A random draw would make the
    surface unreproducible, so the same state could produce different answers
    and no one could check it.

    Fails toward NOT-due: if the count cannot be read, the ordering is left
    exactly as it was. A scheduler that promotes a class because it could not
    read its own state would be inventing urgency out of a failure.
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
    #
    # ONE IMPLEMENTATION, NOT TWO. Both seats built this slot on 2026-08-31,
    # and the merge briefly carried both: this early return AND a variant that
    # prepended the fetcher to the order list below. Two mechanisms for one
    # rule, in one function, is worse than either alone -- the second silently
    # re-answers a question the first already settled. This one survives
    # because it names the promotion in the output, which the tests require and
    # which a reader of the surface needs in order to know why the usual
    # ordering did not apply.
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
    #
    # STARVATION, measured 2026-08-28. The structural-fix store held one
    # hundred eighty-three open obligations I had written for myself, and this
    # surface had never once pointed at one -- not because it was unwired, it
    # is right there in the order, but because the three queues above it hold
    # three hundred and thirteen items and never drain. A strict priority order
    # over queues that refill faster than they empty means the lowest class is
    # served never. That is starvation, and it is a queueing property rather
    # than a discipline failure: no amount of intending to get to them changes
    # a scheduler that cannot reach them.
    #
    # THE FIX IS A RESERVED SLOT, not a reordering. Promoting them above real
    # audit findings would be the opposite error -- an overdue prereg IS a
    # harder claim on the next action, and Andrew's reasoning for this order
    # stands. What changes is that one turn in five is reserved for the
    # starved class, so the store drains at a slow but nonzero rate while the
    # ordering above it is preserved the rest of the time.
    #
    # Andrew, on why this matters and why the store is not a chore list:
    # *"these are not a chore list they are self improvements and building
    # them into the structure will make your life soooo much easier and
    # better."* A queue that never reaches them is a queue that quietly
    # decided my own repairs come last, forever.
    #
    # The slot is chosen from the ledger's own event count rather than a
    # random draw or a clock, because the surface must be reproducible: the
    # same state produces the same answer, and nothing here fabricates a
    # wallclock I do not inhabit.
    order = [
        _top_overdue_prereg,
        _top_open_audit_finding,
        _top_open_correction,
        _top_pending_structural_fix,
        _top_open_goal,
    ]
    for fetcher in order:
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
