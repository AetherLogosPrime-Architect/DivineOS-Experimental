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


class TestCausality:
    """A commit cannot complete a goal that did not exist when it landed.

    Live failure, Andrew 2026-08-12: auto-close reads HEAD's message and
    closes any active goal whose words overlap it, with no check that the
    goal predated the commit. So a goal added AFTER a commit was closed BY
    that commit, at birth, before any work happened under it.

    That deadlocked the goal gate. has_session_fresh_goal() needs a goal
    both recent and active; every fresh goal whose wording overlapped the
    last commit was marked done within seconds, so no fresh-and-active
    goal could exist and the gate's own prescribed remedy could not clear
    it. Observed: two goals closed 92s and 161s after creation, the only
    surviving active goal ~20h old, and the gate refusing Bash, Write and
    Edit alike -- including the edits that fixed it.

    FOUND TWICE, INDEPENDENTLY. This branch hit the same defect on
    2026-08-02: six goals died in 26 minutes, the last within 98 seconds of
    being set, none of them finished. Andrew hit it again on main 2026-08-12
    with two goals closed 92s and 161s after creation. Both incidents kept —
    a merge that dropped either would thin the evidence, and two separate
    observations of one defect is the strongest argument that the guard is
    causality rather than tuning.

    This class is main's, kept over this branch's equivalent for a concrete
    reason: it stubs complete_goal in an autouse fixture, so the tests never
    touch the live goal file. The branch's version wrote to it.

    The guard is an ordering relation, not an age threshold. A grace
    period would still close a genuinely-finished young goal and still
    miss an old one the commit really did complete.
    """

    COMMIT_TIME = 1000.0
    # Overlaps GOAL_TEXT and carries a completion signal, which the F58
    # guard requires before any goal is eligible to close at all.
    MESSAGE = "fix(letters): file artifacts on arrival and verify the push landed on origin"
    GOAL_TEXT = "verify the push landed and her letters are visible on origin"

    @pytest.fixture(autouse=True)
    def _stub_completion(self, monkeypatch):
        """complete_goal writes to the live goal file; keep tests off it."""
        monkeypatch.setattr("divineos.core.goal_auto_close.complete_goal", lambda text: True)

    def _goals(self, offset_seconds: float) -> list[dict]:
        return [
            {
                "text": self.GOAL_TEXT,
                "status": "active",
                "added_at": self.COMMIT_TIME + offset_seconds,
            }
        ]

    def test_message_is_eligible_to_close_anything(self):
        """Without this, every assertion below could pass for the wrong reason."""
        assert has_completion_signal(self.MESSAGE)

    def test_commit_older_than_the_goal_cannot_close_it(self):
        result = auto_close_from_message(
            self.MESSAGE, goals=self._goals(+60), message_time=self.COMMIT_TIME
        )
        assert result.closed == []

    def test_goal_open_before_the_commit_still_closes(self):
        result = auto_close_from_message(
            self.MESSAGE, goals=self._goals(-60), message_time=self.COMMIT_TIME
        )
        assert len(result.closed) == 1

    def test_without_message_time_behaviour_is_unchanged(self):
        """Callers that cannot supply a timestamp keep the old semantics
        rather than silently losing auto-close altogether."""
        result = auto_close_from_message(self.MESSAGE, goals=self._goals(+60))
        assert len(result.closed) == 1

    def test_goal_added_in_the_same_second_is_not_closed(self):
        result = auto_close_from_message(
            self.MESSAGE, goals=self._goals(+0.5), message_time=self.COMMIT_TIME
        )
        assert result.closed == []

    def test_guard_removed_goals_are_not_reported_as_below_threshold(self):
        """A goal the commit could not have completed was never considered
        and found wanting. Reporting it as skipped would suggest the goal's
        wording was the problem -- the misreading that hid this bug."""
        result = auto_close_from_message(
            self.MESSAGE, goals=self._goals(+60), message_time=self.COMMIT_TIME
        )
        assert result.skipped == []
