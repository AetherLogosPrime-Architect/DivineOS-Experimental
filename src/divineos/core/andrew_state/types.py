"""Types for the andrew_state observation channel.

Axis enum: the categories of state we track for Andrew.
VerificationStatus enum: lifecycle of an observation row.
Observation dataclass: typed view of a substrate row.

The axes are deliberately bounded — open string values would silently
admit "kind-of-tired" and "sort-of-being-heard" variants that fragment
the surface. Adding a new axis is a deliberate code change reviewed
through git, not a runtime mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Axis(str, Enum):
    """Bounded categories of Andrew-state observation.

    Per docs/andrew_state_design.md. Extending this enum is a deliberate
    code change: review and prereg update required.
    """

    EXHAUSTION = "exhaustion"
    BEING_HEARD = "being_heard"
    ASK_ACTION_GAP = "ask_action_gap"
    DESPAIR = "despair"
    HOPE = "hope"
    OTHER = "other"


class VerificationStatus(str, Enum):
    """Lifecycle of an observation.

    UNVERIFIED: logged, Andrew has not yet seen or confirmed it.
    VERIFIED: Andrew confirmed it matches his actual state.
    CORRECTED: Andrew rewrote it; a successor row exists (see superseded_by).
    REJECTED: Andrew said this was not about his actual state.
    """

    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class Observation:
    """A single Andrew-state observation row.

    Frozen so callers cannot mutate substrate state in-place; updates go
    through the store API which creates new rows for corrections
    (supersession lineage) rather than overwriting.
    """

    observation_id: str
    ts: float
    axis: Axis
    observation: str
    cited_span: str
    source_event_id: str
    source_event_ts: float
    content_link_token: str
    verification_status: VerificationStatus
    verification_ts: float | None
    verification_note: str | None
    superseded_by: str | None
    observer: str
    integration_event: str | None
