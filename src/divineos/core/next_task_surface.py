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
    finding, or None."""
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
    # Severity order: HIGH > MEDIUM > LOW > INFO. Pick the first
    # highest-severity finding.
    severity_rank = {
        Severity.HIGH: 0,
        Severity.MEDIUM: 1,
        Severity.LOW: 2,
        Severity.INFO: 3,
    }
    sorted_findings = sorted(
        all_findings,
        key=lambda f: (severity_rank.get(f.severity, 99), -f.created_at),
    )
    top = sorted_findings[0]
    line = f"resolve {top.finding_id} [{top.severity.value}]: {top.title}"
    return top.finding_id, _truncate(line)


def _top_open_correction() -> tuple[str, str] | None:
    """Return (correction_id, one-line) for the oldest open Andrew-correction,
    or None."""
    try:
        from divineos.core.andrew_corrections import list_corrections
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        corrections = list_corrections(open_only=True)
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not corrections:
        return None
    # Oldest first — they've been waiting longest.
    sorted_corrections = sorted(corrections, key=lambda c: c.created_at)
    top = sorted_corrections[0]
    cid = getattr(top, "correction_id", None) or getattr(top, "id", "?")
    text = getattr(top, "content", "") or getattr(top, "text", "")
    line = f"integrate correction {cid}: {text}"
    return str(cid), _truncate(line)


def _top_pending_structural_fix() -> tuple[str, str] | None:
    """Return (psf_id, one-line) for the oldest pending structural-fix
    obligation, or None."""
    try:
        from divineos.core.structural_fix_tracker import list_pending
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    try:
        pending = list_pending()
    except Exception:  # noqa: BLE001 - observability boundary
        return None
    if not pending:
        return None
    top = pending[0]
    psf_id = top.get("id", "?")
    excerpt = top.get("content_excerpt", "")
    line = f"address {psf_id}: {excerpt}"
    return psf_id, _truncate(line)


def build_next_task_surface() -> str:
    """Return the NEXT TASK block for pre-response context, or empty string
    when no tasks are pending across all four sources.

    The block contains ONE highest-priority item, named with its source
    so I know what kind of action it needs (assess / resolve / integrate /
    address). The format is intentionally short to keep context overhead
    minimal — the surface is a pointer, not the work.
    """
    # Priority order: overdue prereg > open audit > open correction > psf.
    for fetcher in (
        _top_overdue_prereg,
        _top_open_audit_finding,
        _top_open_correction,
        _top_pending_structural_fix,
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
