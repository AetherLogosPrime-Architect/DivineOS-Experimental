"""Pre-registration type definitions — enums and dataclass.

A pre-registration is a written prediction about a mechanism filed BEFORE
the mechanism runs long enough to produce evidence. The commitment shape is:

* ``mechanism`` — the thing being predicted about (e.g. "incomplete_fix_detector")
* ``claim`` — what the mechanism is supposed to do
* ``success_criterion`` — the specific observable pattern that counts as success
* ``falsifier`` — the specific observable pattern that invalidates the mechanism
* ``review_ts`` — when the pre-registration must be reviewed (ledger-scheduled)
* ``outcome`` — the review's verdict, immutable once recorded

Designed to prevent Goodhart creep: a detector that ships with a pre-registered
falsifier and a scheduled review cannot quietly become a number-up-habit-unchanged
surface, because the review date fires independent of agent memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Outcome(str, Enum):
    """Verdict after reviewing a pre-registration.

    Transitions are one-way: ``OPEN`` -> any terminal state, but terminal states
    do not transition further. To revise a verdict, file a new pre-registration
    that references the old one via ``linked_claim_id`` or a tag. This mirrors
    the append-only ledger philosophy: never rewrite history, always supersede.
    """

    OPEN = "OPEN"  # Not yet reviewed
    SUCCESS = "SUCCESS"  # Success criterion observed
    FAILED = "FAILED"  # Falsifier triggered — mechanism does not do what it claimed
    INCONCLUSIVE = "INCONCLUSIVE"  # Evidence ambiguous; consider re-registration
    DEFERRED = "DEFERRED"  # Need more data; review_ts extended via re-filing


# Actors allowed to record outcomes. Internal actors are rejected to prevent
# the agent from silently flipping its own FAILED pre-regs to SUCCESS. External
# review (user, grok, fresh-Claude, council) is the only path to outcome.
INTERNAL_ACTORS = frozenset(
    {
        "system",
        "assistant",
        "pipeline",
        "divineos",
        "hook",
        "schedule",
        "claude",
    }
)


@dataclass
class PreRegistration:
    """A single pre-registered claim with falsifier and scheduled review."""

    prereg_id: str
    created_at: float
    actor: str
    mechanism: str
    claim: str
    success_criterion: str
    falsifier: str
    review_ts: float
    review_window_days: int
    outcome: Outcome = Outcome.OPEN
    outcome_ts: float | None = None
    outcome_notes: str = ""
    linked_claim_id: str | None = None
    linked_commit: str | None = None
    tags: list[str] = field(default_factory=list)
