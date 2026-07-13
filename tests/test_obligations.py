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

from divineos.core.obligations import (
    Obligation,
    command_references_open_obligation,
    is_substrate_write_command,
)


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


class TestCommandReferencesOpenObligation:
    """Locked-box-trap fix (Andrew 2026-06-11). When a substrate-write
    command's payload contains a reference to one of the open obligation
    kids, that write IS the structural backing landing — let it through.
    The previous gate blocked the very writes that would have backed the
    obligations (filing a prereg that names the kid; committing code that
    references the kid in the message). Bypass-marker use was the
    workaround; this is the structural cure.
    """

    def _ob(self, kid: str, kind: str = "will-shape") -> Obligation:
        return Obligation(kind=kind, knowledge_id=kid, summary="", triggers=["MUST X"])

    def test_matches_full_kid_in_command(self) -> None:
        obs = {
            "unbacked_promises": [self._ob("1d36be4f-1234-5678-9abc-def012345678")],
            "unpaired_observations": [],
        }
        cmd = (
            'divineos prereg file "structural backing for kid '
            "1d36be4f-1234-5678-9abc-def012345678 "
            'per Andrew 2026-06-11"'
        )
        matched = command_references_open_obligation(cmd, obs)
        assert matched == "1d36be4f-1234-5678-9abc-def012345678"

    def test_matches_short_kid_prefix(self) -> None:
        obs = {
            "unbacked_promises": [self._ob("ee96a4f7abcdef1234567890")],
            "unpaired_observations": [],
        }
        cmd = 'divineos prereg file "backing for kid ee96a4f7 — optimizer-DUMB principle locks in"'
        matched = command_references_open_obligation(cmd, obs)
        assert matched == "ee96a4f7"

    def test_matches_unpaired_observation_kid(self) -> None:
        obs = {
            "unbacked_promises": [],
            "unpaired_observations": [self._ob("d69bba1d-xxxx", "correction-pairing")],
        }
        cmd = 'divineos audit submit "follow-up on kid d69bba1d"'
        matched = command_references_open_obligation(cmd, obs)
        assert matched == "d69bba1d"

    def test_no_kid_in_command_returns_none(self) -> None:
        obs = {
            "unbacked_promises": [self._ob("1d36be4f-1234")],
            "unpaired_observations": [],
        }
        cmd = 'divineos prereg file "some new thing unrelated to any open kid"'
        assert command_references_open_obligation(cmd, obs) is None

    def test_empty_obligations_returns_none(self) -> None:
        obs = {"unbacked_promises": [], "unpaired_observations": []}
        cmd = 'divineos prereg file "backing for kid 12345678"'
        assert command_references_open_obligation(cmd, obs) is None

    def test_empty_command_returns_none(self) -> None:
        obs = {
            "unbacked_promises": [self._ob("1d36be4f-1234")],
            "unpaired_observations": [],
        }
        assert command_references_open_obligation("", obs) is None
        assert command_references_open_obligation(None, obs) is None  # type: ignore[arg-type]

    def test_short_kid_below_min_length_does_not_match(self) -> None:
        # Conservative: prefix must be >= 8 hex chars. Shorter kids (test
        # fixtures, edge cases) don't trigger a match on random tokens.
        obs = {
            "unbacked_promises": [self._ob("abc")],  # 3 chars only
            "unpaired_observations": [],
        }
        cmd = "divineos prereg file abc def"
        assert command_references_open_obligation(cmd, obs) is None

    def test_skips_unknown_kid_marker(self) -> None:
        # When obligation has knowledge_id='unknown' (lookup failed), the
        # function ignores it rather than matching the literal word 'unknown'.
        obs = {
            "unbacked_promises": [self._ob("unknown")],
            "unpaired_observations": [],
        }
        cmd = 'divineos prereg file "unknown territory"'
        assert command_references_open_obligation(cmd, obs) is None

    def test_handles_obligation_as_dict_not_dataclass(self) -> None:
        # Defensive: get_pending_obligations may evolve to return dicts
        # alongside dataclasses; the matcher tolerates both shapes.
        obs = {
            "unbacked_promises": [{"knowledge_id": "12345678-aaaa", "triggers": []}],
            "unpaired_observations": [],
        }
        cmd = "divineos prereg file backing for kid 12345678"
        matched = command_references_open_obligation(cmd, obs)
        assert matched == "12345678"

    def test_full_kid_match_preferred_over_prefix(self) -> None:
        # If both forms appear (full id contains its own prefix), the full
        # form should match first (it's the more specific signal).
        full = "1d36be4f-1234-5678-9abc-def012345678"
        obs = {
            "unbacked_promises": [self._ob(full)],
            "unpaired_observations": [],
        }
        cmd = f'divineos prereg file "backs {full} directly"'
        matched = command_references_open_obligation(cmd, obs)
        assert matched == full  # full, not just '1d36be4f'
