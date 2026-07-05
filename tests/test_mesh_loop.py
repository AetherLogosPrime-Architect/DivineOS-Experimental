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

    def test_continue_at_cap_fires_final(self):
        """T5: cap-hit is FIRE_FINAL_CAP_HIT, not skip. Final Meeseeks
        gets the converge_or_stuck prompt; the response IS the closure."""
        decision = decide(IterationState(count=10, max=10, signal="continue"))
        assert decision.action == FireAction.FIRE_FINAL_CAP_HIT
        assert "final Meeseeks" in decision.reason

    def test_continue_over_cap_skips_as_safety_net(self):
        """Over-cap is safety net — final-cap Meeseeks should have terminated
        the loop with done/stuck/escalate. If we somehow got a continue past
        the cap, refuse to fire."""
        decision = decide(IterationState(count=15, max=10, signal="continue"))
        assert decision.action == FireAction.SKIP_CAP_EXCEEDED

    def test_escalate_signal_skips(self):
        """T5: escalate is the third terminal signal — final Meeseeks read
        the thread but couldn't judge convergence. Surface to Andrew."""
        decision = decide(IterationState(count=5, max=10, signal="escalate"))
        assert decision.action == FireAction.SKIP_ESCALATED

    def test_done_with_closure_mode_forced_names_it_in_reason(self):
        """T5: closure_mode=forced (cap-forced close) surfaces distinctly from
        natural convergence — Pop's surface can color them differently."""
        decision = decide(IterationState(count=5, max=10, signal="done", closure_mode="forced"))
        assert decision.action == FireAction.SKIP_CONVERGED
        assert "forced" in decision.reason

    def test_stuck_with_because_surfaces_the_reason(self):
        """T2: stuck_because free-text lets Pop see WHY the seat got stuck
        without guessing."""
        decision = decide(
            IterationState(
                count=3,
                max=10,
                signal="stuck",
                stuck_because="letter-mode context insufficient for this shape",
            )
        )
        assert decision.action == FireAction.SKIP_STUCK
        assert "letter-mode context insufficient" in decision.reason

    def test_reason_is_always_populated(self):
        for state in [
            None,
            IterationState(count=0, max=10, signal="bogus"),
            IterationState(count=0, max=10, signal="done"),
            IterationState(count=0, max=10, signal="stuck"),
            IterationState(count=0, max=10, signal="escalate"),
            IterationState(count=10, max=10, signal="continue"),
            IterationState(count=15, max=10, signal="continue"),
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

    def test_letter_at_cap_fires_final(self, tmp_path: Path):
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
        assert decision.action == FireAction.FIRE_FINAL_CAP_HIT


# ─── Extended-schema fields (T1 loop_class, T4 from_pid, T5 closure_mode) ─


class TestExtendedSchemaFields:
    def test_parse_all_optional_fields(self):
        text = (
            "---\n"
            "iterate_count: 4\n"
            "iterate_max: 10\n"
            "iterate_signal: done\n"
            "loop_class: design\n"
            "from_pid: 24584\n"
            "closure_mode: natural\n"
            "---\n"
            "Body.\n"
        )
        state = parse_iteration_state(text)
        assert state is not None
        assert state.loop_class == "design"
        assert state.from_pid == 24584
        assert state.closure_mode == "natural"

    def test_parse_stuck_because(self):
        text = (
            "---\n"
            "iterate_count: 3\n"
            "iterate_max: 10\n"
            "iterate_signal: stuck\n"
            'stuck_because: "letter-mode context insufficient"\n'
            "---\nBody.\n"
        )
        state = parse_iteration_state(text)
        assert state is not None
        assert state.signal == "stuck"
        assert state.stuck_because == "letter-mode context insufficient"

    def test_optional_fields_default_to_none(self):
        """Backward compat: letters with just iterate_* still parse and fire.
        Optional fields default to None."""
        text = "---\niterate_count: 1\niterate_max: 10\niterate_signal: continue\n---\nBody.\n"
        state = parse_iteration_state(text)
        assert state is not None
        assert state.loop_class is None
        assert state.from_pid is None
        assert state.closure_mode is None
        assert state.stuck_because is None

    def test_non_integer_from_pid_returns_none(self):
        text = (
            "---\n"
            "iterate_count: 1\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "from_pid: not-a-pid\n"
            "---\nBody.\n"
        )
        assert parse_iteration_state(text) is None

    def test_invalid_loop_class_fails_is_valid(self):
        state = IterationState(count=1, max=10, signal="continue", loop_class="marketing")
        assert not state.is_valid()

    def test_invalid_closure_mode_fails_is_valid(self):
        state = IterationState(count=1, max=10, signal="done", closure_mode="whimsical")
        assert not state.is_valid()

    def test_negative_from_pid_fails_is_valid(self):
        state = IterationState(count=1, max=10, signal="continue", from_pid=-5)
        assert not state.is_valid()

    def test_all_valid_loop_classes(self):
        for cls in ("design", "test", "operational", "debug"):
            state = IterationState(count=1, max=10, signal="continue", loop_class=cls)
            assert state.is_valid(), f"{cls} should be valid"

    def test_all_valid_signals(self):
        for sig in (
            "continue",
            "done",
            "stuck",
            "escalate",
            "witness_confirmed",
            "witness_dissent",
        ):
            state = IterationState(count=1, max=10, signal=sig)
            assert state.is_valid(), f"{sig} should be valid"


# ─── Boundary-vantage witness (Aletheia Shape 1 fix) ────────────────────


class TestBoundaryVantageRequired:
    def test_witness_confirmed_signal_skips_as_closed(self):
        """Aletheia confirms closure — the loop is done."""
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(IterationState(count=5, max=10, signal="witness_confirmed"))
        assert decision.action == FireAction.SKIP_WITNESS_CONFIRMED

    def test_witness_dissent_signal_fires_to_restart(self):
        """Aletheia rejects closure — loop restarts iteration."""
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(IterationState(count=5, max=10, signal="witness_dissent"))
        assert decision.action == FireAction.FIRE_WITNESS_DISSENT

    def test_done_with_design_class_flags_pending_witness(self):
        """Identity-formation-tier loop_class defaults to boundary_vantage_required=true.
        Done signal in that state surfaces the PENDING_WITNESS status.
        """
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(IterationState(count=4, max=10, signal="done", loop_class="design"))
        assert decision.action == FireAction.SKIP_CONVERGED
        assert "PENDING_WITNESS" in decision.reason

    def test_done_with_test_class_does_not_require_witness(self):
        """Topic-tier loop_class (test/debug) defaults to boundary_vantage_required=false.
        Done signal in that state does not surface PENDING_WITNESS.
        """
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(IterationState(count=4, max=10, signal="done", loop_class="test"))
        assert decision.action == FireAction.SKIP_CONVERGED
        assert "PENDING_WITNESS" not in decision.reason

    def test_explicit_boundary_vantage_required_overrides_class_default(self):
        """Frontmatter can explicitly require witness even for test-class loops."""
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(
            IterationState(
                count=4,
                max=10,
                signal="done",
                loop_class="test",
                boundary_vantage_required=True,
            )
        )
        assert "PENDING_WITNESS" in decision.reason

    def test_explicit_false_overrides_class_default(self):
        """Frontmatter can explicitly opt-out of witness even for design-class."""
        from divineos.core.mesh_loop import decide as decide_

        decision = decide_(
            IterationState(
                count=4,
                max=10,
                signal="done",
                loop_class="design",
                boundary_vantage_required=False,
            )
        )
        assert "PENDING_WITNESS" not in decision.reason

    def test_no_class_no_explicit_defaults_true(self):
        """If neither loop_class nor boundary_vantage_required is set,
        fail-safe defaults to requiring witness."""
        state = IterationState(count=4, max=10, signal="done")
        assert state.requires_boundary_vantage() is True

    def test_parse_boundary_vantage_required_from_frontmatter(self):
        text = (
            "---\n"
            "iterate_count: 2\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "loop_class: design\n"
            "boundary_vantage_required: true\n"
            "---\nBody.\n"
        )
        state = parse_iteration_state(text)
        assert state is not None
        assert state.boundary_vantage_required is True

    def test_parse_boundary_vantage_required_false(self):
        text = (
            "---\n"
            "iterate_count: 2\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "boundary_vantage_required: false\n"
            "---\nBody.\n"
        )
        state = parse_iteration_state(text)
        assert state is not None
        assert state.boundary_vantage_required is False

    def test_parse_invalid_boundary_vantage_required_returns_none(self):
        text = (
            "---\n"
            "iterate_count: 2\n"
            "iterate_max: 10\n"
            "iterate_signal: continue\n"
            "boundary_vantage_required: maybe\n"
            "---\nBody.\n"
        )
        assert parse_iteration_state(text) is None
