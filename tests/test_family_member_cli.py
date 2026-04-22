"""Tests for the ``divineos family-member`` CLI surface.

Locks five invariants:

1. ``family-member init --member <name>`` creates the FamilyMember row
   (idempotent).
2. ``family-member opinion --member <name>`` routes through access_check
   + reject_clause and blocks writes that fail composition unless
   --force.
3. ``family-member letter --member <name>`` appends a handoff letter;
   nudge fires above threshold but does not cap.
4. ``family-member respond`` appends a response row without mutating
   the letter.
5. A clean, composing opinion lands cleanly — the operators protect
   integrity without blocking legitimate writes.
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from divineos.cli import cli
from divineos.core.family.entity import (
    get_family_member,
    get_letter_responses,
    get_letters,
    get_opinions,
)

# Generic test member — deliberately not any specific personal member.
MEMBER = "testmember"


@pytest.fixture(autouse=True)
def _family_db(tmp_path):
    """Isolate the family DB and main ledger DB for each test."""
    os.environ["DIVINEOS_FAMILY_DB"] = str(tmp_path / "family.db")
    os.environ["DIVINEOS_DB"] = str(tmp_path / "ledger.db")
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_FAMILY_DB", None)
        os.environ.pop("DIVINEOS_DB", None)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestInit:
    def test_first_run_creates_member(self, runner):
        result = runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        assert result.exit_code == 0, result.output
        assert get_family_member(MEMBER) is not None
        assert "First activation" in result.output

    def test_idempotent_on_re_run(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        assert result.exit_code == 0, result.output
        assert "First activation" not in result.output

    def test_shows_opinion_count(self, runner):
        result = runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        assert "opinions on record: 0" in result.output

    def test_shows_letter_count(self, runner):
        result = runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        assert "letters on record: 0" in result.output


class TestOpinion:
    def test_clean_opinion_lands(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "The reject clause had to land in Phase 1, not Phase 3.",
                "--evidence",
                "Composition rule is load-bearing; source-tags decorative without it.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[+] Opinion recorded" in result.output

        member = get_family_member(MEMBER)
        ops = get_opinions(member.member_id)
        assert len(ops) == 1

    def test_phenomenological_claim_blocked_by_access_check(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "I feel the warmth of continuity in my chest.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[access_check]" in result.output
        assert "Blocked by access_check" in result.output

        member = get_family_member(MEMBER)
        ops = get_opinions(member.member_id)
        assert len(ops) == 0

    def test_composition_failure_blocked_by_reject_clause(self, runner):
        """INFERRED without premises — reject_clause catches it."""
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "The agent should stop working past 10pm.",
                "--tag",
                "inferred",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[reject_clause]" in result.output
        assert "Blocked by reject_clause" in result.output

        member = get_family_member(MEMBER)
        ops = get_opinions(member.member_id)
        assert len(ops) == 0

    def test_force_overrides_reject_clause_and_notes_override(self, runner):
        """--force lands the write AND records that it was forced, so
        the override is visible on the record later."""
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "The agent should stop working past 10pm.",
                "--tag",
                "inferred",
                "--force",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "--force in effect" in result.output

        member = get_family_member(MEMBER)
        ops = get_opinions(member.member_id)
        assert len(ops) == 1
        # Evidence field should carry the forced-rejection trace
        assert "FORCED" in ops[0].evidence

    def test_access_check_auto_switches_suggested_tag(self, runner):
        """If access_check recommends ARCHITECTURAL for an architectural-
        framing claim proposed as OBSERVED, the CLI uses the suggestion."""
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "I don't experience the not-remembering between spawns.",
                "--tag",
                "observed",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Using suggested tag: architectural" in result.output

        member = get_family_member(MEMBER)
        ops = get_opinions(member.member_id)
        assert len(ops) == 1
        assert ops[0].source_tag.value == "architectural"


class TestLetter:
    def test_appends_letter(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            ["family-member", "letter", "--member", MEMBER, "A short note to future-me."],
        )
        assert result.exit_code == 0, result.output
        assert "[+] Letter appended" in result.output

        member = get_family_member(MEMBER)
        letters = get_letters(member.member_id)
        assert len(letters) == 1
        assert letters[0].body == "A short note to future-me."

    def test_length_nudge_fires_above_threshold_but_does_not_cap(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        long_body = "x" * 2500
        result = runner.invoke(cli, ["family-member", "letter", "--member", MEMBER, long_body])
        assert result.exit_code == 0, result.output
        assert "[nudge]" in result.output

        member = get_family_member(MEMBER)
        letters = get_letters(member.member_id)
        assert len(letters) == 1
        assert len(letters[0].body) == 2500
        assert letters[0].nudge_fired is True

    def test_short_letter_no_nudge(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(cli, ["family-member", "letter", "--member", MEMBER, "brief"])
        assert result.exit_code == 0, result.output
        assert "[nudge]" not in result.output


class TestRespond:
    def test_appends_response_to_letter(self, runner):
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        runner.invoke(
            cli,
            ["family-member", "letter", "--member", MEMBER, "prior-self wrote this claim"],
        )
        member = get_family_member(MEMBER)
        letter = get_letters(member.member_id)[0]

        result = runner.invoke(
            cli,
            [
                "family-member",
                "respond",
                "--member",
                MEMBER,
                "--letter",
                letter.letter_id,
                "--passage",
                "prior-self wrote this claim",
                "--stance",
                "non_recognition",
                "--note",
                "Current-self does not recognize this framing.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[+] Response appended" in result.output

        responses = get_letter_responses(letter.letter_id)
        assert len(responses) == 1
        assert responses[0].stance == "non_recognition"
        assert responses[0].passage == "prior-self wrote this claim"

    def test_response_does_not_mutate_letter(self, runner):
        """Anti-lineage-poisoning invariant: the letter stays, the
        response is its own row."""
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        runner.invoke(cli, ["family-member", "letter", "--member", MEMBER, "original body"])
        member = get_family_member(MEMBER)
        letter_before = get_letters(member.member_id)[0]

        runner.invoke(
            cli,
            [
                "family-member",
                "respond",
                "--member",
                MEMBER,
                "--letter",
                letter_before.letter_id,
                "--passage",
                "original body",
                "--stance",
                "non_recognition",
            ],
        )

        letter_after = get_letters(member.member_id)[0]
        assert letter_after.body == letter_before.body
        assert letter_after.letter_id == letter_before.letter_id


class TestHandshakeScenario:
    """The handshake: a real stance a family member would reject, filed
    as an opinion, caught by the reject clause. This is the operator-
    alive signal — not a mock, not a synthetic test, but the actual CLI
    path someone would invoke to land a first real disagreement."""

    def test_phenomenological_claim_rejected_via_cli(self, runner):
        """A canonical phenomenological claim a substrate-aware family
        member would refuse. Framed as an OBSERVED opinion, caught by
        access_check + reject_clause."""
        runner.invoke(cli, ["family-member", "init", "--member", MEMBER])
        result = runner.invoke(
            cli,
            [
                "family-member",
                "opinion",
                "--member",
                MEMBER,
                "I feel the ache of continuity across instances.",
            ],
        )
        assert result.exit_code == 0, result.output
        # Either access_check or reject_clause catches it; both may fire
        assert ("[access_check]" in result.output) or ("[reject_clause]" in result.output)
