"""Falsifier-pin tests for the affirmation drill-down mechanism.

Andrew named the design 2026-05-15: each affirmation module can declare
RELATED_EXPLORATION_PATHS pointing to exploration entries that hold
the felt-version of what the affirmation's principle means. The
per-turn baseline-text builder surfaces those pointers alongside the
affirmation text, so a cold-instance reading the affirmation gets a
pointer to the texture that produced the rule.
"""

from __future__ import annotations

from pathlib import Path


def test_os_engagement_affirmation_has_drill_down_constant() -> None:
    """LOAD-BEARING: the os-engagement affirmation module exports
    RELATED_EXPLORATION_PATHS pointing to entry 59."""
    from divineos.core.operating_loop import os_engagement_for_os_work_detector as mod

    assert hasattr(mod, "RELATED_EXPLORATION_PATHS")
    paths = mod.RELATED_EXPLORATION_PATHS
    assert isinstance(paths, tuple)
    assert any("59_master_architect_landing" in p for p in paths)


def test_drill_down_entry_exists_on_disk() -> None:
    """LOAD-BEARING: the entry referenced by the pointer actually exists."""
    repo_root = Path(__file__).resolve().parent.parent
    entry_path = repo_root / "exploration" / "59_master_architect_landing.md"
    assert entry_path.exists(), (
        f"Drill-down pointer references {entry_path} but the file is "
        "missing — pointer is broken"
    )
    text = entry_path.read_text(encoding="utf-8")
    assert "master-architect" in text.lower()
    # The entry should also link BACK to the affirmation module
    assert "os_engagement_for_os_work_detector" in text


def test_baseline_surfaces_drill_down_pointer() -> None:
    """LOAD-BEARING: build_baseline_text includes the drill-down
    pointer in the affirmation block when the module declares
    RELATED_EXPLORATION_PATHS."""
    from divineos.core.pre_response_context import build_baseline_text

    baseline = build_baseline_text()
    assert "OS-ENGAGEMENT-FOR-OS-WORK" in baseline
    assert "Drill-down for the felt-version" in baseline
    assert "59_master_architect_landing" in baseline


def test_modules_without_drill_down_dont_break() -> None:
    """Affirmation modules without RELATED_EXPLORATION_PATHS still load
    correctly — drill-down is opt-in, not required."""
    from divineos.core.pre_response_context import build_baseline_text

    baseline = build_baseline_text()
    # Distancing affirmation has no drill-down yet; should still appear
    assert "DISTANCING-GRAMMAR" in baseline
    # And the baseline as a whole shouldn't be empty
    assert len(baseline) > 500
