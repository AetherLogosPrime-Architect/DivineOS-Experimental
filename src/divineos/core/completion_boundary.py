"""Completion-boundary detection — Phase 1b of the rudder redesign.

The redesigned rudder's question is "is the artifact wired up?" The
companion question is "did the agent ever say it was finished?" —
which the agent currently answers only implicitly, by moving on to
the next thing. ``divineos complete`` makes that answer explicit:
the agent files a ``COMPLETION_BOUNDARY_DETECTED`` event naming the
artifact and its wire-up status. The rudder can later cross-check
contract acks against these boundaries.

Per brief v2.1 §Point 5 (Option A+B trigger detection): completion
boundaries are detected from PR-merge primary signal AND `divineos
complete` secondary signal AND nag-not-block fallback when neither
fires within a long window. This module owns the secondary path —
the explicit operator-filed boundary. PR-merge detection is wired
elsewhere (existing watchmen flow); the nag-not-block fallback is a
Phase 2 concern.

Boundary types (brief v2.1 §Point 3 refinement 5): every emitted
event carries a ``boundary_type`` field. ``"explicit_complete"`` is
the default (this CLI path); ``"pr_merge"`` and ``"tests_green"`` are
reserved for the watchmen and CI integrations.

**Event-distinction note (forensic readers):** this module's event
``COMPLETION_BOUNDARY_DETECTED`` is the *operator-filed* signal —
no fire_id binding, no spectrum. The companion event from the
``moral_compass`` path, ``RUDDER_ACK_RETRACTED``, is *fire-bound* —
it carries fire_id + spectrum + observation_id. They are distinct
on purpose: a forensic reader who sees both can tell whether a
retraction was filed as a free-standing operator action (boundary)
or as the wired=retracted field on a specific ack (rudder).

Pure-ish: the only side effect is appending a single event to the
ledger. No DB schema changes, no separate store. Boundaries are
read back via the ledger's ``get_events(event_type=...)`` API like
any other event.
"""

from __future__ import annotations

from dataclasses import dataclass

# Valid wire-up status values — must match the contract module so a
# boundary filed via `divineos complete` lines up with what a
# subsequent rudder-ack would attest.
WIRE_STATUS_VALUES = frozenset({"yes", "no", "partial", "retracted"})

# Brief v2.1 §Point 3 refinement 5 boundary-type vocabulary.
# - explicit_complete: operator filed via `divineos complete` (this CLI)
# - pr_merge: watchmen detected a merge of an artifact PR
# - tests_green: CI integration confirmed tests pass post-wire-up
BOUNDARY_TYPES = frozenset({"explicit_complete", "pr_merge", "tests_green"})


@dataclass(frozen=True)
class CompletionBoundary:
    """Result of recording a completion boundary."""

    event_id: str
    artifact_reference: str
    wired: str
    boundary_type: str
    next_plan: str | None
    depends_on: str | None
    note: str


def record_completion(
    artifact_reference: str,
    wired: str,
    next_plan: str | None = None,
    depends_on: str | None = None,
    source: str = "operator",
    boundary_type: str = "explicit_complete",
) -> CompletionBoundary:
    """Emit a ``COMPLETION_BOUNDARY_DETECTED`` event.

    Validates inputs at the boundary — empty artifact_reference and
    out-of-vocabulary wired raise ValueError. When ``wired`` is not
    "yes", ``next_plan`` is required (the same rule the contract-ack
    enforces — a boundary filed mid-wire-up must name the next step).

    Returns the CompletionBoundary with the event_id from the ledger
    write so callers can confirm persistence.
    """
    if not artifact_reference or not artifact_reference.strip():
        raise ValueError("artifact_reference is required and must be non-empty")
    wired_norm = wired.strip().lower()
    if wired_norm not in WIRE_STATUS_VALUES:
        raise ValueError(f"wired must be one of {sorted(WIRE_STATUS_VALUES)}, got {wired!r}")
    boundary_norm = boundary_type.strip().lower()
    if boundary_norm not in BOUNDARY_TYPES:
        raise ValueError(
            f"boundary_type must be one of {sorted(BOUNDARY_TYPES)}, got {boundary_type!r}"
        )
    if wired_norm != "yes" and not (next_plan and next_plan.strip()):
        raise ValueError(f"wired={wired_norm!r} requires a next_plan — name the next step")

    artifact_clean = artifact_reference.strip()
    next_clean: str | None = (next_plan or "").strip() or None
    depends_clean: str | None = (depends_on or "").strip() or None
    payload = {
        "artifact_reference": artifact_clean,
        "wired": wired_norm,
        "boundary_type": boundary_norm,
        "next_plan": next_clean,
        "depends_on": depends_clean,
        "source": source,
    }

    from divineos.core.ledger import log_event

    # validate=False: COMPLETION_BOUNDARY_DETECTED is new in Phase 1b
    # and not yet in the EventValidator catalog. Same pattern as the
    # Phase 1a RUDDER_ACK_REJECTION_ESCALATED emission. The validator
    # will learn the schema in a later Phase (4+) once the event has
    # stabilized through observe-mode use.
    event_id = log_event(
        event_type="COMPLETION_BOUNDARY_DETECTED",
        actor=source,
        payload=payload,
        validate=False,
    )

    return CompletionBoundary(
        event_id=str(event_id),
        artifact_reference=artifact_clean,
        wired=wired_norm,
        boundary_type=boundary_norm,
        next_plan=next_clean,
        depends_on=depends_clean,
        note=f"Completion boundary recorded for {artifact_clean} (wired={wired_norm}).",
    )


def list_recent_completions(limit: int = 20) -> list[dict]:
    """Return recent COMPLETION_BOUNDARY_DETECTED payloads, newest first.

    Best-effort wrapper over the ledger; returns [] if the ledger is
    unavailable. Used by the CLI for ``divineos complete --list``.

    Ordering: explicitly sorted by ``timestamp`` descending here so the
    "newest first" contract holds regardless of what ``get_events``
    decides to default to in the future. Without this sort, an upstream
    change to ``get_events`` ordering would silently reorder
    ``divineos complete --list`` output.
    """
    try:
        from divineos.core.ledger import get_events
    except ImportError:
        return []
    try:
        events = get_events(event_type="COMPLETION_BOUNDARY_DETECTED", limit=limit)
    except Exception:  # noqa: BLE001
        return []
    out = list(events)
    out.sort(key=lambda e: e.get("timestamp") or 0, reverse=True)
    return out
