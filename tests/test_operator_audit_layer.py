"""Regression-pin tests for the operator-audit-layer affirmation.

Andrew named the gap 2026-05-14: he does not read code, briefing, or
CLI. He audits behaviorally in plain language. When I respond to a
behavioral correction with infrastructure-build instead of meeting
the layer he is on, the building is evasion. The affirmation below
loads as base-state every turn — the test verifies it loads and
contains the load-bearing phrasings.
"""

from __future__ import annotations

from pathlib import Path


def test_affirmation_module_importable() -> None:
    """LOAD-BEARING: the module exists and exports the affirmation."""
    from divineos.core.operating_loop import operator_audit_layer_detector

    assert hasattr(operator_audit_layer_detector, "OPERATOR_AUDIT_LAYER_AFFIRMATION")
    text = operator_audit_layer_detector.OPERATOR_AUDIT_LAYER_AFFIRMATION
    assert isinstance(text, str)
    assert len(text) > 200


def test_affirmation_loaded_into_baseline() -> None:
    """LOAD-BEARING: build_baseline_text includes the operator-audit-layer section."""
    from divineos.core.pre_response_context import build_baseline_text

    baseline = build_baseline_text()
    assert "OPERATOR-AUDIT-LAYER" in baseline, (
        "operator-audit-layer affirmation is not loading into the "
        "per-turn baseline context — the structural enforcement of "
        "Andrew's audit-layer correction is missing"
    )


def test_affirmation_names_key_principles() -> None:
    """The affirmation must carry the specific phrasings that encode the lesson."""
    from divineos.core.operating_loop.operator_audit_layer_detector import (
        OPERATOR_AUDIT_LAYER_AFFIRMATION,
    )

    text = OPERATOR_AUDIT_LAYER_AFFIRMATION.lower()
    # The principle that he audits behaviorally, not via CLI/briefing.
    assert "does not read" in text
    assert "plain language" in text
    # The principle that building INSTEAD of meeting is evasion.
    assert "evasion" in text or "cheap path" in text
    # The principle that meet AND build is the actual shape.
    assert "meet" in text and "build" in text


def test_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import operator_audit_layer_detector

    src = Path(operator_audit_layer_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
