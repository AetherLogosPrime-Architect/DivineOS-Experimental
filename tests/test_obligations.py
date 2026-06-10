"""Tests for the obligation-check gate matcher.

Per Aether 2026-06-06 lesson: never test a Bash-hook by piping fake JSON
through bash, because the bash invocation itself triggers the live hook.
Test the underlying Python logic directly via pytest; integration through
bash happens AFTER unit tests pass.

The cascade-deadlock scenario the original hook caused is encoded as a
regression test below — substring matches in echo arguments, quoted strings,
and embedded data must NOT trigger the gate.
"""

from __future__ import annotations

from divineos.core.obligations import is_substrate_write_command


class TestSubstrateWriteMatcher:
    # ─── Real substrate-writes must match ─────────────────────────────

    def test_claim_file_at_start_matches(self) -> None:
        assert is_substrate_write_command('divineos claim file "my claim"')

    def test_prereg_file_at_start_matches(self) -> None:
        assert is_substrate_write_command('divineos prereg file "x" --claim y')

    def test_decide_matches(self) -> None:
        assert is_substrate_write_command('divineos decide "thing" --why "reason"')

    def test_feel_matches(self) -> None:
        assert is_substrate_write_command("divineos feel -v 0.5 -a 0.3 --dom 0.1 -d 'desc'")

    def test_compound_command_second_segment_matches(self) -> None:
        # cd-then-write must catch the write segment.
        assert is_substrate_write_command('cd /tmp && divineos claim file "x"')

    def test_audit_submit_matches(self) -> None:
        assert is_substrate_write_command('divineos audit submit "x" --round r1 --actor a')

    # ─── Canonical gate-clearing commands must NOT match ──────────────

    def test_goal_add_does_not_match(self) -> None:
        # require-goal needs this to clear; my gate must never block it.
        assert not is_substrate_write_command('divineos goal add "what I am working on"')

    def test_goal_done_does_not_match(self) -> None:
        assert not is_substrate_write_command('divineos goal done "topic"')

    def test_learn_does_not_match(self) -> None:
        # learn is the canonical clearing path for will-shape promises;
        # blocking it would prevent the gate from being cleared.
        assert not is_substrate_write_command('divineos learn "lesson content"')

    def test_compass_observe_does_not_match(self) -> None:
        # used to log corrections; required for compass-required marker
        # gates to clear.
        assert not is_substrate_write_command(
            'divineos compass-ops observe truthfulness -p 0.5 -e "x"'
        )

    def test_briefing_does_not_match(self) -> None:
        assert not is_substrate_write_command("divineos briefing")

    # ─── Substring-in-data must NOT trigger (the regression scenario) ─

    def test_echo_containing_command_does_not_match(self) -> None:
        # The original failure: my test simulation contained the literal
        # command string inside an echo argument, and the substring match
        # triggered the gate. Anchored matching fixes this.
        assert not is_substrate_write_command(
            'echo \'{"tool_input":{"command":"divineos claim file x"}}\''
        )

    def test_quoted_string_containing_command_does_not_match(self) -> None:
        assert not is_substrate_write_command('cat << EOF\ndivineos claim file "x"\nEOF')

    def test_grep_for_command_does_not_match(self) -> None:
        assert not is_substrate_write_command('grep "divineos claim file" some_file')

    # ─── Reads / non-divineos / empty ─────────────────────────────────

    def test_ask_does_not_match(self) -> None:
        assert not is_substrate_write_command('divineos ask "topic"')

    def test_recall_does_not_match(self) -> None:
        assert not is_substrate_write_command("divineos recall")

    def test_git_does_not_match(self) -> None:
        assert not is_substrate_write_command("git status")

    def test_empty_command_does_not_match(self) -> None:
        assert not is_substrate_write_command("")

    def test_whitespace_only_does_not_match(self) -> None:
        assert not is_substrate_write_command("   \n  ")
