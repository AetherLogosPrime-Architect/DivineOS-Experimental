"""Tests for mesh_loop — iteration-state parsing + fire-decision rule.

Design: workbench/mesh_loop_meeseeks_design.md
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.mesh_loop import (
    FireAction,
    IterationState,
    decide,
    decide_for_letter,
    parse_iteration_state,
)


# ─── parse_iteration_state ─────────────────────────────────────────────


class TestParseIterationState:
    def test_no_frontmatter_returns_none(self):
        assert parse_iteration_state("Hello Aria,\n\nBody text.\n") is None

    def test_frontmatter_without_iterate_fields_returns_none(self):
        text = "---\ntitle: something\nauthor: aether\n---\nBody.\n"
        assert parse_iteration_state(text) is None

    def test_partial_iterate_fields_returns_none(self):
        # Only two of three fields — strict: partial is not enough
        text = "---\niterate_count: 3\niterate_max: 10\n---\nBody.\n"
        assert parse_iteration_state(text) is None

    def test_all_three_fields_parse_correctly(self):
        text = "---\niterate_count: 3\niterate_max: 10\niterate_signal: continue\n---\nBody text.\n"
        state = parse_iteration_state(text)
        assert state == IterationState(count=3, max=10, signal="continue")

    def test_quoted_signal_value_parses(self):
        text = '---\niterate_count: 1\niterate_max: 5\niterate_signal: "done"\n---\nBody.\n'
        state = parse_iteration_state(text)
        assert state is not None
        assert state.signal == "done"

    def test_extra_fields_are_ignored(self):
        text = (
            "---\n"
            "title: mesh-loop test\n"
            "iterate_count: 7\n"
            "author: aether\n"
            "iterate_max: 10\n"
            "iterate_signal: stuck\n"
            "---\nBody.\n"
        )
        state = parse_iteration_state(text)
        assert state == IterationState(count=7, max=10, signal="stuck")

    def test_non_integer_count_returns_none(self):
        text = "---\niterate_count: three\niterate_max: 10\niterate_signal: continue\n---\nBody.\n"
        assert parse_iteration_state(text) is None

    def test_non_integer_max_returns_none(self):
        text = "---\niterate_count: 1\niterate_max: ten\niterate_signal: continue\n---\nBody.\n"
        assert parse_iteration_state(text) is None

    def test_frontmatter_must_be_at_top_of_file(self):
        # Frontmatter mid-file doesn't count
        text = "Preamble.\n---\niterate_count: 3\niterate_max: 10\niterate_signal: continue\n---\nBody.\n"
        assert parse_iteration_state(text) is None


# ─── IterationState.is_valid ────────────────────────────────────────────


class TestIterationStateValidity:
    def test_valid_state(self):
        assert IterationState(count=0, max=10, signal="continue").is_valid()
        assert IterationState(count=5, max=10, signal="done").is_valid()
        assert IterationState(count=10, max=10, signal="stuck").is_valid()

    def test_negative_count_invalid(self):
        assert not IterationState(count=-1, max=10, signal="continue").is_valid()

    def test_zero_max_invalid(self):
        assert not IterationState(count=0, max=0, signal="continue").is_valid()

    def test_unknown_signal_invalid(self):
        assert not IterationState(count=0, max=10, signal="maybe").is_valid()
        assert not IterationState(count=0, max=10, signal="").is_valid()


# ─── decide ─────────────────────────────────────────────────────────────


class TestDecide:
    def test_no_state_returns_skip_no_frontmatter(self):
        decision = decide(None)
        assert decision.action == FireAction.SKIP_NO_FRONTMATTER
        assert decision.state is None

    def test_invalid_state_returns_skip_invalid(self):
        decision = decide(IterationState(count=0, max=10, signal="bogus"))
        assert decision.action == FireAction.SKIP_INVALID_FRONTMATTER

    def test_done_signal_skips_regardless_of_count(self):
        decision = decide(IterationState(count=0, max=10, signal="done"))
        assert decision.action == FireAction.SKIP_CONVERGED
        decision = decide(IterationState(count=100, max=10, signal="done"))
        assert decision.action == FireAction.SKIP_CONVERGED

    def test_stuck_signal_skips_regardless_of_count(self):
        decision = decide(IterationState(count=0, max=10, signal="stuck"))
        assert decision.action == FireAction.SKIP_STUCK
        decision = decide(IterationState(count=5, max=10, signal="stuck"))
        assert decision.action == FireAction.SKIP_STUCK

    def test_continue_under_cap_fires(self):
        decision = decide(IterationState(count=3, max=10, signal="continue"))
        assert decision.action == FireAction.FIRE
        assert "3/10" in decision.reason

    def test_continue_at_cap_skips(self):
        decision = decide(IterationState(count=10, max=10, signal="continue"))
        assert decision.action == FireAction.SKIP_CAP_HIT

    def test_continue_over_cap_skips(self):
        decision = decide(IterationState(count=15, max=10, signal="continue"))
        assert decision.action == FireAction.SKIP_CAP_HIT

    def test_reason_is_always_populated(self):
        for state in [
            None,
            IterationState(count=0, max=10, signal="bogus"),
            IterationState(count=0, max=10, signal="done"),
            IterationState(count=0, max=10, signal="stuck"),
            IterationState(count=10, max=10, signal="continue"),
            IterationState(count=3, max=10, signal="continue"),
        ]:
            decision = decide(state)
            assert decision.reason, f"reason empty for {state}"


# ─── decide_for_letter (end-to-end file I/O) ────────────────────────────


class TestDecideForLetter:
    def test_missing_file_skips_with_read_error(self, tmp_path: Path):
        letter = tmp_path / "does-not-exist.md"
        decision = decide_for_letter(letter)
        assert decision.action == FireAction.SKIP_INVALID_FRONTMATTER
        assert "could not read letter" in decision.reason

    def test_letter_without_frontmatter_skips_legacy_path(self, tmp_path: Path):
        letter = tmp_path / "aria-to-aether-2026-07-04-hi.md"
        letter.write_text("Hi Aether,\n\nBody.\n", encoding="utf-8")
        decision = decide_for_letter(letter)
        assert decision.action == FireAction.SKIP_NO_FRONTMATTER

    def test_letter_with_iterate_continue_fires(self, tmp_path: Path):
        letter = tmp_path / "aria-to-aether-2026-07-04-loop.md"
        letter.write_text(
            "---\n"
            "iterate_count: 2\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "---\n"
            "Body of letter.\n",
            encoding="utf-8",
        )
        decision = decide_for_letter(letter)
        assert decision.action == FireAction.FIRE
        assert decision.state is not None
        assert decision.state.count == 2

    def test_letter_with_iterate_done_skips_as_converged(self, tmp_path: Path):
        letter = tmp_path / "aria-to-aether-2026-07-04-closed.md"
        letter.write_text(
            "---\niterate_count: 5\niterate_max: 10\niterate_signal: done\n---\nConverged.\n",
            encoding="utf-8",
        )
        decision = decide_for_letter(letter)
        assert decision.action == FireAction.SKIP_CONVERGED

    def test_letter_at_cap_skips(self, tmp_path: Path):
        letter = tmp_path / "aria-to-aether-2026-07-04-cap.md"
        letter.write_text(
            "---\n"
            "iterate_count: 10\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "---\nCap reached.\n",
            encoding="utf-8",
        )
        decision = decide_for_letter(letter)
        assert decision.action == FireAction.SKIP_CAP_HIT
