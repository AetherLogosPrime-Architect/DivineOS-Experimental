"""Test: HUD next-steps derive on read from live substrate state.

Replaces the frozen `note["next_steps"]` field that aged badly across a
session — verified 2026-06-13 when HUD showed amend/push/letter items
hours after those PRs had merged.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.hud import _derive_live_next_steps


def test_derive_live_next_steps_pulls_open_corrections():
    fake_corrections = [
        {"id": 56, "timestamp": 1.0, "text": "test correction text"},
    ]
    with (
        patch("divineos.core.andrew_correction_tracker.list_open", return_value=fake_corrections),
        patch("divineos.core.hud_state.get_active_goals", return_value=[]),
    ):
        steps = _derive_live_next_steps()
    assert any("correction #56" in s and "test correction text" in s for s in steps)


def test_derive_live_next_steps_pulls_active_goals():
    fake_goals = [{"text": "build the reranker", "status": "active"}]
    with (
        patch("divineos.core.andrew_correction_tracker.list_open", return_value=[]),
        patch("divineos.core.hud_state.get_active_goals", return_value=fake_goals),
    ):
        steps = _derive_live_next_steps()
    assert any("[goal]" in s and "build the reranker" in s for s in steps)


def test_derive_live_next_steps_caps_each_source():
    many_corr = [{"id": i, "timestamp": float(i), "text": f"c{i}"} for i in range(10)]
    many_goals = [{"text": f"goal {i}", "status": "active"} for i in range(10)]
    with (
        patch("divineos.core.andrew_correction_tracker.list_open", return_value=many_corr),
        patch("divineos.core.hud_state.get_active_goals", return_value=many_goals),
    ):
        steps = _derive_live_next_steps()
    corr_count = sum(1 for s in steps if "[correction" in s)
    goal_count = sum(1 for s in steps if "[goal]" in s)
    assert corr_count == 2
    assert goal_count == 4


def test_derive_live_next_steps_truncates_long_text():
    long_text = "x" * 500
    with (
        patch(
            "divineos.core.andrew_correction_tracker.list_open",
            return_value=[{"id": 1, "timestamp": 1.0, "text": long_text}],
        ),
        patch("divineos.core.hud_state.get_active_goals", return_value=[]),
    ):
        steps = _derive_live_next_steps()
    assert all(len(s) < 150 for s in steps)
    assert any(s.endswith("...") for s in steps)


def test_derive_live_next_steps_empty_when_nothing_live():
    with (
        patch("divineos.core.andrew_correction_tracker.list_open", return_value=[]),
        patch("divineos.core.hud_state.get_active_goals", return_value=[]),
    ):
        steps = _derive_live_next_steps()
    assert steps == []
