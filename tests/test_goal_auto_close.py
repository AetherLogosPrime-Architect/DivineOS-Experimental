"""Tests for goal_auto_close — closure-discipline structural fix."""

from __future__ import annotations

import json

import pytest

from divineos.core.goal_auto_close import (
    AutoCloseResult,
    _tokenize,
    auto_close_from_message,
    has_completion_signal,
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
        # Includes completion signal ("landed") so F58 gate passes.
        msg = "feat(core): synchronicity detector landed — temporal co-occurrence across stores Pillar VI"
        result = auto_close_from_message(msg)
        assert result.closed
        assert any("synchronicity" in c.lower() for c in result.closed)

    def test_low_overlap_does_not_close(self, hud_dir):
        hud_dir([_goal("write a complete onboarding tutorial")])
        result = auto_close_from_message("fix typo in README")
        assert result.closed == []

    def test_threshold_controls_sensitivity(self, hud_dir):
        hud_dir([_goal("knowledge voids detector for the substrate")])
        # Includes completion signal so F58 gate passes; threshold gates overlap.
        strict = auto_close_from_message(
            "fix(core): knowledge voids landed — detect sparse regions",
            threshold=0.99,
        )
        assert strict.closed == []

        hud_dir([_goal("knowledge voids detector for the substrate")])
        loose = auto_close_from_message(
            "fix(core): knowledge voids landed — detect sparse regions",
            threshold=0.3,
        )
        assert loose.closed != []

    def test_done_goal_skipped(self, hud_dir):
        hud_dir([_goal("synchronicity detector", status="done")])
        # Completion signal present, but goal already done so skipped.
        result = auto_close_from_message("fix(core): synchronicity detector landed")
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
        # F58: real completion signal added — conv-commit prefix + "landed".
        msg = (
            "feat(core): synchronicity detector landed — temporal co-occurrence across substrate stores\n\n"
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


class TestF58CompletionSignal:
    """F58 (Aletheia Round 7): overlap alone must not close.

    A commit that reverts, is WIP, still-debugging, or in-progress
    must NOT mark the goal DONE even if it names all the goal's
    substantive tokens. Verified empirically in the Round 7 finding:
    four of five non-completion commits were closing the goal
    permanently. The fix requires completion-shape (conv-commit type
    OR completion verb) AND absence of reversal/WIP signals.
    """

    def test_revert_commit_does_not_close(self, hud_dir):
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message("revert(core): synchronicity detector — broken")
        assert result.closed == []

    def test_wip_commit_does_not_close(self, hud_dir):
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message("WIP synchronicity detector stack")
        assert result.closed == []

    def test_still_debugging_does_not_close(self, hud_dir):
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message("still debugging synchronicity detector, not done yet")
        assert result.closed == []

    def test_started_work_does_not_close(self, hud_dir):
        """No completion verb, no conv-commit prefix — must not close
        even though 'started' isn't itself a reversal signal.
        """
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message("started synchronicity detector work")
        assert result.closed == []

    def test_real_completion_still_closes(self, hud_dir):
        """The happy path — conv-commit type + completion verb — MUST close."""
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message(
            "feat(core): synchronicity detector landed for stack 3 (#123)"
        )
        assert result.closed != []

    def test_bare_completion_verb_closes(self, hud_dir):
        """Free-form completion verb (no conv-commit prefix) also counts."""
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message("synchronicity detector shipped and merged to main")
        assert result.closed != []

    def test_broken_overrides_completion(self, hud_dir):
        """Even if a completion word appears, a reversal signal must veto."""
        hud_dir([_goal("ship synchronicity detector for stack 3")])
        result = auto_close_from_message(
            "shipped synchronicity detector but it's broken, rolling back"
        )
        assert result.closed == []


class TestHasCompletionSignal:
    """Unit tests for the F58 completion-shape helper."""

    def test_conv_commit_type_counts(self):
        assert has_completion_signal("fix(core): thing")
        assert has_completion_signal("feat(hud): slot")
        assert has_completion_signal("chore(deps): bump")

    def test_bare_completion_verbs_count(self):
        assert has_completion_signal("synchronicity landed")
        assert has_completion_signal("shipped the detector")
        assert has_completion_signal("resolved the bug")

    def test_reversal_vetoes(self):
        assert not has_completion_signal("revert(core): shipped foo")
        assert not has_completion_signal("shipped X but broken")
        assert not has_completion_signal("WIP synchronicity")
        assert not has_completion_signal("still debugging synchronicity")

    def test_no_signal_returns_false(self):
        assert not has_completion_signal("started X work")
        assert not has_completion_signal("looking at the detector")
        assert not has_completion_signal("")
        assert not has_completion_signal("some random text")


class TestCommitCannotCloseGoalsItPredates:
    """The time-travel defect, and the livelock it caused.

    ``divineos goal auto-close`` with no --message reads ``git log -1``, and
    every CLI command is a lifecycle checkpoint that can fire it. So one
    stale HEAD was re-matched against every open goal forever, including
    goals created long after that commit existed.

    On 2026-08-02 that produced a livelock: the goal doorman refuses
    substrate edits without a session-fresh goal; I set one; the next command
    re-ran auto-close against a stale HEAD sharing its vocabulary; the goal
    was marked done seconds later; the doorman refused again. Six goals died
    in 26 minutes, the last within 98 seconds of being set, none finished.
    The gate demanding a goal was fed by the mechanism destroying it — the
    same shape as the bypass livelock Aria demonstrated the same day.

    A commit cannot complete work that did not exist when it was written.
    That is causality, not a heuristic, so it is checked rather than tuned.
    """

    MSG = "feat(x): verify the widget ships. Verified and complete, all tests pass."

    def _goal(self, added_at):
        return [{"text": "verify the widget ships", "added_at": added_at, "status": "active"}]

    def test_a_goal_created_after_the_commit_is_not_considered(self):
        import time

        now = time.time()
        r = auto_close_from_message(self.MSG, goals=self._goal(now - 60), commit_time=now - 600)
        assert r.closed == []
        assert r.skipped and r.skipped[0][1] == -1.0, (
            "must be skipped on causality, distinctly from a low-overlap skip"
        )

    def test_a_goal_created_before_the_commit_is_still_considered(self):
        """The filter must not become a blanket refusal — otherwise nothing
        ever auto-closes and the discipline it automates dies quietly."""
        import time

        now = time.time()
        r = auto_close_from_message(self.MSG, goals=self._goal(now - 900), commit_time=now - 600)
        assert r.skipped == [], "an older goal must reach the overlap check"

    def test_unknown_commit_time_does_not_filter(self):
        """None means UNKNOWN, not 'everything is eligible' — but it must not
        silently change behaviour for callers that cannot supply a time."""
        import time

        now = time.time()
        r = auto_close_from_message(self.MSG, goals=self._goal(now - 60), commit_time=None)
        assert not any(s[1] == -1.0 for s in r.skipped)
