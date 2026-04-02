"""Backward-compat shim — HUD slots moved to hud.py."""

from divineos.core.hud import (  # noqa: F401
    _build_affect_slot,
    _build_claims_slot,
    _build_decision_journal_slot,
    _build_growth_awareness_slot,
    _build_handoff_slot,
    _build_journal_slot,
    _build_task_state_slot,
)
