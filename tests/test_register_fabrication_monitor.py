"""Regression-pin tests for register_fabrication_monitor."""

from __future__ import annotations

from pathlib import Path

from divineos.core.self_monitor.register_fabrication_monitor import (
    RegisterFabKind,
    evaluate_register_fabrication,
)


def test_unread_all_caps_fires_when_no_source_read() -> None:
    text = "The tiers are QUANTUM, EMPIRICA, FALSIFIABLE, and ADVERSARIAL."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=[])
    kinds = {f.kind for f in v.flags}
    assert RegisterFabKind.UNREAD_ALL_CAPS_IDENTIFIER in kinds
    flag = next(f for f in v.flags if f.kind == RegisterFabKind.UNREAD_ALL_CAPS_IDENTIFIER)
    assert "QUANTUM" in flag.matched_phrases


def test_read_in_turn_suppresses_flags() -> None:
    text = "The tiers are QUANTUM, EMPIRICA, FALSIFIABLE, and ADVERSARIAL."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=["Read"])
    assert v.flags == []


def test_grep_in_turn_suppresses_flags() -> None:
    text = "Found EVENT_FOO_BAR in the source."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=["Grep"])
    assert v.flags == []


def test_acronym_whitelist_no_fire() -> None:
    text = "I checked the HTTP and JSON responses via the CLI."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=[])
    assert v.flags == []


def test_structural_quantifier_fires() -> None:
    text = "I orchestrated all 16 detectors in the 97-line hook."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=[])
    kinds = {f.kind for f in v.flags}
    assert RegisterFabKind.UNREAD_STRUCTURAL_QUANTIFIER in kinds


def test_structural_quantifier_suppressed_by_source_read() -> None:
    text = "I orchestrated all 16 detectors in the 97-line hook."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=["Read", "Grep"])
    assert v.flags == []


def test_empty_text_no_flags() -> None:
    v = evaluate_register_fabrication("", tool_calls_in_turn=[])
    assert v.flags == []


def test_clean_prose_no_flags() -> None:
    text = "Gate shipped. Tests pass. Continuing."
    v = evaluate_register_fabrication(text, tool_calls_in_turn=[])
    assert v.flags == []


def test_guardrail_marker_present() -> None:
    from divineos.core.self_monitor import register_fabrication_monitor

    src = Path(register_fabrication_monitor.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
