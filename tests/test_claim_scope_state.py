"""Tests for the claim-scope state slice wiring.

Aletheia audit round-a1e7f4c92b6d, 2026-07-15. The verify-claim gate
emits a directive asking for short-correction shape, but the directive
was decorative because nothing enforced it — full re-composition after
a Stop-block produced duplicate posts. The wiring here exposes the
state slice that Aether's ResponseScopeIntercept
(src/divineos/hooks/response_scope_intercept.py) reads to LOCK reply-emit
that doesn't match short-correction shape.

These tests verify the state-slice contract between operating_loop_audit
(the directive emitter) and response_scope_intercept (the enforcer).
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop_audit import (
    _clear_claim_scope,
    _claim_scope_state,
    _mark_claim_scope_active,
    _unverified_claim_gate_reason,
    get_claim_scope_state,
)


@pytest.fixture(autouse=True)
def reset_state():
    """Ensure each test starts from a clean state and leaves it clean."""
    _clear_claim_scope()
    yield
    _clear_claim_scope()


def test_default_state_inactive():
    """Fresh state: no directive active, empty directive text."""
    state = get_claim_scope_state()
    assert state == {
        "claim_scope_active": False,
        "claim_scope_directive_text": "",
    }


def test_mark_active_sets_both_fields():
    """Marking active sets both the flag AND the directive text."""
    text = "VERIFY-CLAIM GATE — some directive body."
    _mark_claim_scope_active(text)
    state = get_claim_scope_state()
    assert state["claim_scope_active"] is True
    assert state["claim_scope_directive_text"] == text


def test_clear_resets_to_default():
    """Clearing resets both fields to their default (inactive) values."""
    _mark_claim_scope_active("some directive")
    _clear_claim_scope()
    state = get_claim_scope_state()
    assert state == {
        "claim_scope_active": False,
        "claim_scope_directive_text": "",
    }


def test_get_state_returns_fresh_dict_not_reference():
    """Contract: mutating the returned dict must NOT mutate module state.

    The host Stop hook that reads this must not be able to accidentally
    corrupt the internal state by mutating the return value.
    """
    _mark_claim_scope_active("original directive")
    state = get_claim_scope_state()
    state["claim_scope_active"] = False
    state["claim_scope_directive_text"] = "mutated"
    # Module-level state should be untouched
    assert _claim_scope_state["active"] is True
    assert _claim_scope_state["directive_text"] == "original directive"


def test_repeated_mark_active_replaces_directive():
    """A new directive fire overwrites the prior directive text."""
    _mark_claim_scope_active("first directive")
    _mark_claim_scope_active("second directive")
    state = get_claim_scope_state()
    assert state["claim_scope_active"] is True
    assert state["claim_scope_directive_text"] == "second directive"


def test_directive_emit_marks_scope_active():
    """When _unverified_claim_gate_reason emits its directive, the
    claim-scope state must be marked active with the exact returned text.
    This is the wire that closes the enforcement loop — the gate that
    ASKS is also the trigger that sets the LOCK-CONDITION for the gate
    that REFUSES."""
    findings_log = {
        "unverified_claim": [{"trigger": "tests passed", "claim_kind": "tests", "severity": "high"}]
    }
    returned = _unverified_claim_gate_reason(findings_log, addressed_to_father=True)
    assert returned is not None
    state = get_claim_scope_state()
    assert state["claim_scope_active"] is True
    # The state's directive text must exactly match what the gate returned
    # (so the enforcer can cite the specific ask that wasn't honored).
    assert state["claim_scope_directive_text"] == returned


def test_directive_not_emitted_leaves_state_inactive():
    """If the gate does NOT emit a directive (no findings), the state
    stays inactive. Guards against accidental activation.
    """
    findings_log = {"unverified_claim": []}
    returned = _unverified_claim_gate_reason(findings_log, addressed_to_father=True)
    assert returned is None
    state = get_claim_scope_state()
    assert state["claim_scope_active"] is False


def test_state_shape_matches_response_scope_intercept_contract():
    """Contract test: the keys ResponseScopeIntercept.scan() expects
    (per its module docstring) must be exactly what get_claim_scope_state
    returns. If either side changes the contract, this fails loud so the
    wire can be re-aligned."""
    _mark_claim_scope_active("any directive")
    state = get_claim_scope_state()
    # Per src/divineos/hooks/response_scope_intercept.py docstring:
    #   accumulated_state.get("claim_scope_active") -> bool
    #   accumulated_state.get("claim_scope_directive_text", "") -> str
    assert "claim_scope_active" in state
    assert isinstance(state["claim_scope_active"], bool)
    assert "claim_scope_directive_text" in state
    assert isinstance(state["claim_scope_directive_text"], str)
