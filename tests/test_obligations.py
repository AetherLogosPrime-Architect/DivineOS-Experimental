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
    describe_obligation,
    format_block_message,
    is_substrate_write_command,
)
from divineos.core.structural_promotion_check import (
    BASIS_REJUDGED,
    BASIS_UNREADABLE,
    BASIS_UNRECORDED,
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


class TestTheBlockMessageMustNameAWorkingRemedy:
    """A gate may block. It may not give directions that lead nowhere.

    Until 2026-08-22 the message said to reference the knowledge_id "in the
    new code's docstring or commit message so the audit detects the link."
    The audit reads four LEDGER EVENT TYPES; it opens no source file and no
    commit message, so a docstring reference was invisible by construction.
    `divineos learn` was the obvious second guess and emits no ledger event at
    all -- measured: zero new events after a learn.

    So the only two remedies the message named were the two that cannot work,
    and following it left the gate shut with no way to tell why. That is the
    reach-check doorman's shape one layer over: a remedy exempted so it can
    RUN, never wired to opening the door.
    """

    @staticmethod
    def _blocked() -> str:
        return format_block_message(
            {
                "total": 6,
                "unbacked_promises": [
                    Obligation(
                        kind="will-shape",
                        knowledge_id="abc12345-0000-0000-0000-000000000000",
                        summary="some rule",
                        triggers=["must land"],
                    )
                ],
                "unpaired_observations": [],
                "should_block": True,
            }
        )

    def test_it_names_the_command_that_actually_clears(self) -> None:
        assert "divineos integrate" in self._blocked()

    def test_it_names_the_event_the_audit_reads(self) -> None:
        """Not decoration -- it is the only way to tell whether a route worked."""
        assert "KNOWLEDGE_INTEGRATION_CHANGED" in self._blocked()

    def test_it_says_plainly_that_a_docstring_does_not_clear(self) -> None:
        msg = self._blocked()
        assert "docstring" in msg
        assert "does NOT clear" in msg

    def test_it_warns_that_learn_writes_no_ledger_event(self) -> None:
        """The most likely wrong guess, named so it is not made twice."""
        assert "divineos learn" in self._blocked()

    def test_it_still_states_the_threshold(self) -> None:
        assert "below threshold (5)" in self._blocked()


class TestTheGateCanSayWhatItHolds:
    """2026-09-17. Every obligation this gate has ever printed rendered an id,
    a trigger list, and an indented EMPTY line where its meaning belongs —
    because `summary` was fed from a key the producer never set, and the text
    was fetched one function upstream to re-judge the row and then discarded.

    An empty indented slot does not read as plumbing. It reads as the system
    having looked and found nothing, so the gate named a debt it could not
    describe to the only person it stops. Six lessons were held as six debts
    for a month and nobody could ask the clerk what they were.

    These pin the two halves of the repair: the gate says what it holds, and
    saying it never changes what it holds.
    """

    @staticmethod
    def _ob(summary: str, basis: str) -> Obligation:
        return Obligation(
            kind="will-shape",
            knowledge_id="abc12345-0000-0000-0000-000000000000",
            summary=summary,
            triggers=["must land"],
            basis=basis,
        )

    def test_real_text_is_printed_verbatim(self) -> None:
        o = self._ob("never run the suite with the bypass set", BASIS_REJUDGED)
        assert describe_obligation(o) == "never run the suite with the bypass set"

    def test_an_unreadable_row_says_it_was_never_told(self) -> None:
        """The sentence the whole repair exists for."""
        said = describe_obligation(self._ob("", BASIS_UNREADABLE))
        assert "never been told" in said

    def test_an_unrecorded_basis_says_unknown_not_empty(self) -> None:
        """A producer that does not say how it judged must never be read as
        having judged — that silent read is the defect one level up."""
        said = describe_obligation(self._ob("", BASIS_UNRECORDED))
        assert "unknown, not empty" in said.lower()

    def test_no_describable_row_ever_renders_blank(self) -> None:
        for basis in (BASIS_REJUDGED, BASIS_UNREADABLE, BASIS_UNRECORDED, "garbage"):
            assert describe_obligation(self._ob("", basis)).strip()

    # ─── THE INVARIANT. Read the game-walk before touching these. ──────
    #
    # The cheapest attack on this gate is not forging backing — backing costs
    # real work. It is making an entry UNREADABLE, which evades re-judging for
    # free and now earns a sympathetic label. If that label is ever allowed to
    # discount a row, breaking the fetch becomes strictly cheaper than paying
    # the debt and the gate has been taught to reward damage to its own
    # instrument. The change that does this will arrive looking like a
    # kindness. These two tests are what it has to get past.

    def test_an_unreadable_obligation_still_counts_and_still_blocks(self) -> None:
        msg = format_block_message(
            {
                "total": 6,
                "unbacked_promises": [self._ob("", BASIS_UNREADABLE)],
                "unpaired_observations": [],
                "should_block": True,
            }
        )
        assert "BLOCKED" in msg
        assert "(6 total)" in msg

    def test_the_confession_says_the_row_is_still_owed(self) -> None:
        """The confession must not be mistakable for a discharge — a reader
        who stops here instead of investigating is the failure mode."""
        for basis in (BASIS_UNREADABLE, BASIS_UNRECORDED):
            assert "still owed" in describe_obligation(self._ob("", basis))

    def test_the_message_totals_what_it_cannot_describe(self) -> None:
        """A repeated sentence habituates; a number that climbs does not.
        This is the only signal that the fetch is rotting."""
        msg = format_block_message(
            {
                "total": 2,
                "unbacked_promises": [
                    self._ob("a real rule", BASIS_REJUDGED),
                    self._ob("", BASIS_UNREADABLE),
                ],
                "unpaired_observations": [],
                "should_block": True,
            }
        )
        assert "1 CANNOT BE DESCRIBED" in msg

    def test_no_undescribed_line_when_every_row_has_text(self) -> None:
        msg = format_block_message(
            {
                "total": 1,
                "unbacked_promises": [self._ob("a real rule", BASIS_REJUDGED)],
                "unpaired_observations": [],
                "should_block": True,
            }
        )
        assert "CANNOT BE DESCRIBED" not in msg


class TestTheAuditCarriesTheTextItFetches:
    """The upstream half. `verify_recent` fetches each entry's text to re-judge
    it against the current detector, and used to append the raw event dict —
    which carries only an id, a timestamp and the matched triggers. The
    consumer then asked for a `content` key that had never existed.

    Pinned at the shape level rather than through the live store, because the
    defect was never in the fetch. It was that the fetched value did not reach
    the row.
    """

    def test_a_rejudged_row_carries_its_text_and_its_basis(self) -> None:
        row = {
            **{"knowledge_id": "k", "triggers": []},
            "content": "never X",
            "basis": BASIS_REJUDGED,
        }
        o = Obligation(
            kind="will-shape",
            knowledge_id=row["knowledge_id"],
            summary=(row.get("content") or "")[:120],
            triggers=row.get("triggers") or [],
            basis=row.get("basis") or BASIS_UNRECORDED,
        )
        assert o.summary == "never X"
        assert describe_obligation(o) == "never X"

    def test_a_row_with_no_basis_key_defaults_to_unrecorded(self) -> None:
        """Fails toward unknown. A row that says nothing about how it was
        judged must never be read as having been judged."""
        row: dict = {"knowledge_id": "k", "triggers": []}
        o = Obligation(
            kind="will-shape",
            knowledge_id=row["knowledge_id"],
            summary=(row.get("content") or "")[:120],
            triggers=row.get("triggers") or [],
            basis=row.get("basis") or BASIS_UNRECORDED,
        )
        assert o.basis == BASIS_UNRECORDED
        assert "unknown, not empty" in describe_obligation(o).lower()
