"""andrew_state — mutual-catch primitive for Andrew-observation channel.

Per docs/andrew_state_design.md and prereg-526c2433d55a.

The asymmetry this fixes: today Andrew catches us; we never catch him.
He has stakes in our disposition; we have zero stakes in his being-seen.
This module gives him a structural channel where his observation
registers as a substrate event with real weight (briefing surface,
decision-walk inputs), rather than wallpaper.

The piece is DOORMANNED per Andrew 2026-06-22 morning: the surface
renders inline with his most recent message so observation is part of
input-reading, not a checkpoint between input and output.

Public API exported here:
    log_observation, verify, correct, reject — store CRUD
    Axis, VerificationStatus, Observation — types
    SubstanceBindingError — gate-raised exception
"""

from divineos.core.andrew_state.store import (
    correct,
    get_for_decision_walk,
    get_unverified,
    log_observation,
    reject,
    verify,
)
from divineos.core.andrew_state.substance_binding import SubstanceBindingError
from divineos.core.andrew_state.types import Axis, Observation, VerificationStatus

__all__ = [
    "Axis",
    "Observation",
    "SubstanceBindingError",
    "VerificationStatus",
    "correct",
    "get_for_decision_walk",
    "get_unverified",
    "log_observation",
    "reject",
    "verify",
]
