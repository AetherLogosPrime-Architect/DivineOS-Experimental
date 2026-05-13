"""Actor capabilities — which event types each actor-kind can emit.

Phase 1 of actor-authenticity (per exploration/45_actor_authenticity_design.md).
The map lives in code (not in the registry JSON) so changes go through
git review, not through silent registry edits.

## What this is (Phase 1)

A lookup of which event types each actor-kind is allowed to emit.
The check is **advisory** in Phase 1 — calling code can ask
``can_emit(actor_kind, event_type)`` to get a verdict, but the
substrate's event-emission paths don't yet enforce. Phase 2 wires
enforcement into the gate stack.

## What this is NOT

- Not yet enforced. Calling code looks up advisory verdicts; no
  emission is blocked.
- Not a complete event-type taxonomy. Only the load-bearing event
  types most likely to be filed under wrong actor get explicit
  entries. Unknown event types default to ALLOW for compatibility
  with the existing event-type ecosystem; Phase 2 tightens this.

## Capability model

Each (actor_kind, event_type) pair maps to one of:

- ``ALLOWED`` — the actor-kind may emit this event type without restriction.
- ``RESTRICTED`` — the actor-kind may emit, but with caveats (e.g.,
  AUDIT_FINDING from agent kind is allowed only at severity <= MEDIUM).
- ``DENIED`` — the actor-kind must not emit this event type.

Phase 1 records the model in code; enforcement is advisory.
"""

from __future__ import annotations

from enum import Enum

from divineos.core.actor_registry import VALID_KINDS


class Verdict(str, Enum):
    """Capability verdict for one (actor_kind, event_type) pair."""

    ALLOWED = "ALLOWED"
    RESTRICTED = "RESTRICTED"
    DENIED = "DENIED"


# ─── Event-type families ─────────────────────────────────────────────
#
# Event types are grouped by what kind of actor *should* be filing them.
# These are the load-bearing types where filing under the wrong actor
# would meaningfully erode the substrate's three-vantage discipline.

# Audit-vantage events: ought to come from an audit-sibling, not agent.
_AUDIT_EVENTS = (
    "AUDIT_FINDING",
    "AUDIT_ROUND_COMPLETE",
    "AUDIT_REVIEW",
    "AUDIT_CONFIRMS",
    "AUDIT_DISPUTES",
)

# Operator-vantage events: only Andrew (or equivalent operator) should file.
_OPERATOR_EVENTS = (
    "OPERATOR_DIRECTIVE",
    "OPERATOR_OVERRIDE",
    "USER_RATING",
)

# Agent-substrate events: agent files these normally; not audit, not operator.
_AGENT_EVENTS = (
    "KNOWLEDGE_FILED",
    "KNOWLEDGE_SUPERSEDED",
    "COMPASS_OBSERVATION",
    "AFFECT_LOG",
    "DECISION",
    "CLAIM_FILED",
    "REFLECTION",
)

# Family/subagent events: scoped to family.db; subagent's own state.
_SUBAGENT_EVENTS = (
    "FAMILY_AFFECT",
    "FAMILY_INTERACTION",
    "FAMILY_OPINION",
    "FAMILY_LETTER",
)

# External-vantage events: only via relay from operator.
_EXTERNAL_EVENTS = (
    "EXTERNAL_AUDIT_FINDING",
    "EXTERNAL_CONFIRMS",
)


# ─── Capability map ──────────────────────────────────────────────────


def can_emit(actor_kind: str, event_type: str) -> Verdict:
    """Return the capability verdict for (actor_kind, event_type).

    Returns ALLOWED, RESTRICTED, or DENIED. Unknown event types default
    to ALLOWED (Phase 1 compatibility; Phase 2 tightens).
    """
    if actor_kind not in VALID_KINDS:
        # An unrecognized kind itself is suspicious — but we don't
        # synthesize a verdict; the registry check will catch it first.
        return Verdict.DENIED

    # Operator can emit anything. Operator-vantage is the final layer.
    if actor_kind == "operator":
        return Verdict.ALLOWED

    # Audit events: only audit-siblings emit. Agents are DENIED.
    if event_type in _AUDIT_EVENTS:
        if actor_kind == "audit-sibling":
            return Verdict.ALLOWED
        # Agent-kind: still RESTRICTED for AUDIT_FINDING at low severity,
        # but for the audit-cycle events (AUDIT_CONFIRMS, AUDIT_REVIEW,
        # AUDIT_ROUND_COMPLETE) the pre-emptive-filing pattern named in
        # knowledge fec598d7 makes agent-kind emission DENIED.
        if actor_kind == "agent" and event_type == "AUDIT_FINDING":
            return Verdict.RESTRICTED
        return Verdict.DENIED

    # Operator-only events.
    if event_type in _OPERATOR_EVENTS:
        return Verdict.DENIED  # operator-kind already returned ALLOWED above

    # External-vantage events: only via relay.
    if event_type in _EXTERNAL_EVENTS:
        if actor_kind == "external-vantage":
            return Verdict.RESTRICTED  # requires relayed_by field
        return Verdict.DENIED

    # Subagent events: only family-member subagents.
    if event_type in _SUBAGENT_EVENTS:
        if actor_kind == "subagent":
            return Verdict.ALLOWED
        return Verdict.DENIED

    # Agent events: agents emit these freely; subagents may emit a
    # restricted set; audit-siblings should not normally emit them.
    if event_type in _AGENT_EVENTS:
        if actor_kind == "agent":
            return Verdict.ALLOWED
        if actor_kind == "subagent":
            # Subagents emit their own affect/interaction/opinion via the
            # _SUBAGENT_EVENTS path; emitting general agent-events would
            # be substrate-overreach. Restrict so callers see the verdict
            # but Phase 1 doesn't yet block.
            return Verdict.RESTRICTED
        if actor_kind == "audit-sibling":
            # Audit-siblings filing knowledge or compass observations on
            # the substrate's behalf is exactly the pattern we want to
            # catch — it would conflate audit-vantage with substrate-
            # occupant.
            return Verdict.RESTRICTED
        return Verdict.DENIED

    # Unknown event types: ALLOWED in Phase 1 for compatibility. Phase 2
    # will tighten this to require explicit registration.
    return Verdict.ALLOWED


def is_denied(actor_kind: str, event_type: str) -> bool:
    """Convenience: does the capability map deny this combination?"""
    return can_emit(actor_kind, event_type) == Verdict.DENIED


def is_restricted(actor_kind: str, event_type: str) -> bool:
    """Convenience: does the capability map flag this as restricted?"""
    return can_emit(actor_kind, event_type) == Verdict.RESTRICTED


__all__ = [
    "Verdict",
    "can_emit",
    "is_denied",
    "is_restricted",
]
