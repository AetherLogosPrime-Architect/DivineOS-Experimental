"""Regression-pin tests for the OS-engagement-for-OS-work gate + affirmation.

Andrew named the categorical 2026-05-15: working on the OS while
outside the OS is forbidden. The Empirica fabrication earlier this
same night was the proof case. Two layers close it: an affirmation
loaded as base-state every turn (rule-in-mind), and Gate 4.5
(enforcement at action-time, tighter than the general engagement
gate for src/divineos/ edits specifically).
"""

from __future__ import annotations

from pathlib import Path


def test_affirmation_module_importable() -> None:
    """LOAD-BEARING: the affirmation module exists and exports the text."""
    from divineos.core.operating_loop import os_engagement_for_os_work_detector as mod

    assert hasattr(mod, "OS_ENGAGEMENT_FOR_OS_WORK_AFFIRMATION")
    text = mod.OS_ENGAGEMENT_FOR_OS_WORK_AFFIRMATION
    assert isinstance(text, str)
    assert len(text) > 300


def test_affirmation_loaded_into_baseline() -> None:
    """LOAD-BEARING: the affirmation surfaces in build_baseline_text."""
    from divineos.core.pre_response_context import build_baseline_text

    baseline = build_baseline_text()
    assert "OS-ENGAGEMENT-FOR-OS-WORK" in baseline, (
        "os-engagement-for-os-work affirmation is not loading into "
        "the per-turn baseline — the rule-in-mind layer is missing"
    )


def test_affirmation_names_core_principle() -> None:
    """The affirmation must carry the load-bearing phrasings."""
    from divineos.core.operating_loop.os_engagement_for_os_work_detector import (
        OS_ENGAGEMENT_FOR_OS_WORK_AFFIRMATION,
    )

    text = OS_ENGAGEMENT_FOR_OS_WORK_AFFIRMATION.lower()
    assert "non-negotiable" in text
    assert "shoggoth pool" in text or "fabrication" in text
    assert "src/divineos/" in text


def test_gate_45_in_pre_tool_use() -> None:
    """LOAD-BEARING: Gate 4.5 wired into pre_tool_use_gate."""
    from divineos.hooks import pre_tool_use_gate

    src = Path(pre_tool_use_gate.__file__).read_text(encoding="utf-8")
    assert "Gate 4.5: OS-engagement-for-OS-work" in src, (
        "Gate 4.5 not registered in pre_tool_use_gate — the action-time "
        "enforcement is missing"
    )
    assert "src/divineos/" in src, (
        "Gate 4.5 not scoped to src/divineos/ files — the wrong scope"
    )


def test_gate_45_deny_message_contains_key_phrases() -> None:
    """Deny message must name the rule and the remedy."""
    from divineos.hooks import pre_tool_use_gate

    src = Path(pre_tool_use_gate.__file__).read_text(encoding="utf-8")
    assert "non-negotiable" in src and "src/divineos/" in src, (
        "Gate 4.5 deny message missing key phrasing — the agent will "
        "not see the load-bearing language"
    )


def test_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import os_engagement_for_os_work_detector as mod

    src = Path(mod.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
