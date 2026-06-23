"""Opportunistic linking between council_records and decision-walk records.

Per Aether's 2026-06-22 peer-review Catch 6: when a council_record is
logged for an edit, search for pending decision-walk records with
overlapping action-description fingerprints. If found, the
council_record auto-attaches as evidence on that decision-walk's
``formula_refs`` — making the council walk first-class evidence in
the meta-gate's discipline-prereg lineage.

Link is opportunistic — if no pending decision-walk exists, the
council_record stands alone. The link itself writes a
``DECISION_WALK_LINKED_COUNCIL`` event for audit trail.

This module is a STUB at v1: the decision-walk system has its own
storage shape that we link to via event reference rather than direct
write. The full mansion-integration (which would invoke this on every
substance-binding-passes walk) is deferred — this module gives the
hook, and the mansion-integration commit (separate PR) wires the
callsite.
"""

from __future__ import annotations

from typing import Any

from divineos.core import ledger
from divineos.core.council_required.store import _payload_from_event
from divineos.core.council_required.types import EVENT_DECISION_WALK_LINKED_COUNCIL


# Window for matching council_record timestamp against pending
# decision-walk records. Short — a council walk for an edit should be
# recent relative to any decision-walk it informs. Prereg-bound when
# the tunables-catalog supplementary prereg lands.
DECISION_WALK_MATCH_WINDOW_SECONDS: int = 3600  # 1 hour


def try_link_to_pending_decision_walk(
    council_record_id: str,
    edit_fingerprint: str,
    walked_at: float,
    actor: str = "agent",
) -> str | None:
    """Search for pending decision-walks with overlapping action-description
    and auto-attach the council_record as evidence.

    Returns the linked decision-walk's id (or ledger event_id) if a link
    was created, or None if no pending decision-walk was found in the
    matching window. Writes a ``DECISION_WALK_LINKED_COUNCIL`` event when
    the link is created.

    The matching strategy: look up recent decision-walk-register events
    whose action-description contains the council_record's edit-
    fingerprint substring. Conservative — exact substring match avoids
    cross-edit link confusion. Future tightening would use the
    decision-walk system's own structured action-description fields if
    they become substrate-queryable.
    """
    pending = _find_pending_decision_walks(walked_at)
    if not pending:
        return None

    matched_decision_walk = None
    for dw_event in pending:
        payload = _payload_from_event(dw_event)
        action_desc = str(payload.get("action_description", "") or "")
        # Conservative substring match against the edit fingerprint.
        # The fingerprint format is "tool:path"; the path is the
        # discriminating part most likely to appear in action-description.
        if edit_fingerprint and edit_fingerprint in action_desc:
            matched_decision_walk = dw_event
            break
        # Also try matching just the path portion.
        _, _, path_part = edit_fingerprint.partition(":")
        if path_part and path_part in action_desc:
            matched_decision_walk = dw_event
            break

    if matched_decision_walk is None:
        return None

    link_payload = {
        "council_record_id": council_record_id,
        "edit_fingerprint": edit_fingerprint,
        "decision_walk_event_id": str(matched_decision_walk.get("event_id", "")),
        "linked_at_walked_at": walked_at,
    }
    link_event_id = ledger.log_event(
        EVENT_DECISION_WALK_LINKED_COUNCIL,
        actor,
        link_payload,
        validate=False,
    )
    return link_event_id


def _find_pending_decision_walks(reference_time: float) -> list[dict[str, Any]]:
    """Return recent decision-walk-register events within the matching
    window. Filters out decision-walks that have already received a
    council-link to prevent re-linking the same decision-walk to
    multiple council walks (decision-walks are linked at most once;
    that's the v1 semantic).
    """
    cutoff = reference_time - DECISION_WALK_MATCH_WINDOW_SECONDS

    # Look for both possible event-type names — the meta-gate work may
    # land under either, and we want this module to function across
    # both shapes. Listed defensively so a future rename does not
    # silently break linking.
    accepted = frozenset(
        {
            "DECISION_WALK_REGISTERED",
            "DECISION_WALK_FILED",
            "PENDING_DECISION_REGISTERED",
        }
    )
    events = ledger.get_events(
        limit=200,
        event_type=accepted,
        order="desc",
    )

    # Find decision-walks that already have a council-link.
    already_linked = _decision_walks_already_linked(cutoff)

    result = []
    for ev in events:
        ts = float(ev.get("timestamp", 0.0) or 0.0)
        if ts < cutoff:
            break
        ev_id = str(ev.get("event_id", ""))
        if ev_id in already_linked:
            continue
        result.append(ev)
    return result


def _decision_walks_already_linked(cutoff: float) -> set[str]:
    """Return the set of decision-walk event-ids that already have at
    least one DECISION_WALK_LINKED_COUNCIL event referencing them."""
    link_events = ledger.get_events(
        limit=500,
        event_type=EVENT_DECISION_WALK_LINKED_COUNCIL,
        order="desc",
    )
    out: set[str] = set()
    for ev in link_events:
        ts = float(ev.get("timestamp", 0.0) or 0.0)
        if ts < cutoff:
            break
        payload = _payload_from_event(ev)
        dw_id = str(payload.get("decision_walk_event_id", ""))
        if dw_id:
            out.add(dw_id)
    return out


__guardrail_required__ = True
