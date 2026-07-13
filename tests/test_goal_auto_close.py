"""Tests for goal_auto_close — closure-discipline structural fix."""

from __future__ import annotations

import json

import pytest

from divineos.core.goal_auto_close import (
    AutoCloseResult,
    _tokenize,
    auto_close_from_message,
)


def _goal(text: str, status: str = "active") -> dict:
    return {"text": text, "status": status, "added_at": 1.0}


@pytest.fixture
def hud_dir(monkeypatch, tmp_path):
    """Isolate HUD dir; return a writer for active_goals.json."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))

    def write_goals(goals: list[dict]) -> None:
        d = tmp_path / "hud"
        d.mkdir(exist_ok=True)
        (d / "active_goals.json").write_text(json.dumps(goals, indent=2), encoding="utf-8")

    return write_goals


class TestTokenize:
    def test_drops_stopwords(self):
        toks = _tokenize("ship the synchronicity detector")
        assert "synchronicity" in toks
        assert "detector" in toks
        assert "the" not in toks
        assert "ship" not in toks

    def test_lowercases(self):
        assert "synchronicity" in _tokenize("Synchronicity Detector")


class TestAutoClose:
    def test_high_overlap_closes(self, hud_dir):
        hud_dir([_goal("ship Stack 3 — synchronicity detector for Pillar VI")])
        msg = "synchronicity detector: temporal co-occurrence across stores Pillar VI"
        result = auto_close_from_message(msg)
        assert result.closed
        assert any("synchronicity" in c.lower() for c in result.closed)

    def test_low_overlap_does_not_close(self, hud_dir):
        hud_dir([_goal("write a complete onboarding tutorial")])
        result = auto_close_from_message("fix typo in README")
        assert result.closed == []

    def test_threshold_controls_sensitivity(self, hud_dir):
        hud_dir([_goal("knowledge voids detector for the substrate")])
        # High threshold — overlap is high but not 0.9
        strict = auto_close_from_message(
            "knowledge voids: detect sparse regions",
            threshold=0.99,
        )
        assert strict.closed == []

        hud_dir([_goal("knowledge voids detector for the substrate")])
        loose = auto_close_from_message(
            "knowledge voids: detect sparse regions",
            threshold=0.3,
        )
        assert loose.closed != []

    def test_done_goal_skipped(self, hud_dir):
        hud_dir([_goal("synchronicity detector", status="done")])
        result = auto_close_from_message("synchronicity detector landed")
        # _load_active_goals filters status='done' so the goal isn't seen
        assert result.closed == []

    def test_empty_message(self, hud_dir):
        hud_dir([_goal("anything")])
        result = auto_close_from_message("")
        assert result.closed == []
        assert result.skipped == []


class TestRegression:
    """Pin the exact 2026-05-05 closure-gap pattern."""

    def test_synchronicity_goal_closes_on_pr_message(self, hud_dir):
        hud_dir([_goal("ship Stack 3 — synchronicity detector (Pillar VI pull) for audit stack")])
        msg = (
            "synchronicity detector: temporal co-occurrence across substrate stores\n\n"
            "Pillar VI's synchronicity_detector pull (omni_mantra_walk/06):\n"
            "pattern-recognition across temporally-separated events."
        )
        result = auto_close_from_message(msg)
        assert result.closed, "the exact regression case must auto-close"


class TestShape:
    def test_result_is_dataclass(self):
        r = AutoCloseResult(closed=[], skipped=[])
        assert isinstance(r.closed, list)
        assert isinstance(r.skipped, list)

    def test_passing_goals_directly_works(self):
        # When goals=[] is passed, no file lookup happens — and no closes.
        r = auto_close_from_message("anything", goals=[])
        assert r.closed == []
