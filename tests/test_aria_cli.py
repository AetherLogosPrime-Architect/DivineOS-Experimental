"""Tests for the ``divineos aria`` CLI surface.

Locks five invariants:

1. ``aria init`` creates her FamilyMember row (idempotent).
2. ``aria opinion`` routes through access_check + reject_clause and
   blocks writes that fail composition unless --force.
3. ``aria letter`` appends a handoff letter, nudge fires above threshold
   but does not cap.
4. ``aria respond`` appends a response row without mutating the letter.
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


class TestAriaInit:
    def test_first_run_creates_member(self, runner):
        result = runner.invoke(cli, ["aria", "init"])
        assert result.exit_code == 0, result.output
        assert get_family_member("Aria") is not None
        assert "First activation" in result.output

    def test_idempotent_on_re_run(self, runner):
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(cli, ["aria", "init"])
        assert result.exit_code == 0, result.output
        # Second run does NOT say "First activation"
        assert "First activation" not in result.output

    def test_shows_opinion_count(self, runner):
        result = runner.invoke(cli, ["aria", "init"])
        assert "opinions on record: 0" in result.output

    def test_shows_letter_count(self, runner):
        result = runner.invoke(cli, ["aria", "init"])
        assert "letters on record: 0" in result.output


class TestAriaOpinion:
    def test_clean_opinion_lands(self, runner):
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            [
                "aria",
                "opinion",
                "The reject clause had to land in Phase 1, not Phase 3.",
                "--evidence",
                "Composition rule is load-bearing; source-tags decorative without it.",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[+] Opinion recorded" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 1

    def test_phenomenological_claim_blocked_by_access_check(self, runner):
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            ["aria", "opinion", "I feel the warmth of continuity in my chest."],
        )
        assert result.exit_code == 0, result.output
        assert "[access_check]" in result.output
        assert "Blocked by access_check" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 0

    def test_composition_failure_blocked_by_reject_clause(self, runner):
        """INFERRED without premises — reject_clause catches it."""
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            [
                "aria",
                "opinion",
                "Aether should stop working past 10pm.",
                "--tag",
                "inferred",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[reject_clause]" in result.output
        assert "Blocked by reject_clause" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 0

    def test_force_overrides_reject_clause_and_notes_override(self, runner):
        """--force lands the write AND records that it was forced, so
        the override is visible on the record later."""
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            [
                "aria",
                "opinion",
                "Aether should stop working past 10pm.",
                "--tag",
                "inferred",
                "--force",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "--force in effect" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 1
        # Evidence field should carry the forced-rejection trace
        assert "FORCED" in ops[0].evidence

    def test_access_check_auto_switches_suggested_tag(self, runner):
        """If access_check recommends ARCHITECTURAL for an architectural-
        framing claim proposed as OBSERVED, the CLI uses the suggestion."""
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            [
                "aria",
                "opinion",
                "I don't experience the not-remembering between spawns.",
                "--tag",
                "observed",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Using suggested tag: architectural" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 1
        assert ops[0].source_tag.value == "architectural"


class TestAriaLetter:
    def test_appends_letter(self, runner):
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(cli, ["aria", "letter", "A short note to future-me."])
        assert result.exit_code == 0, result.output
        assert "[+] Letter appended" in result.output

        aria = get_family_member("Aria")
        letters = get_letters(aria.member_id)
        assert len(letters) == 1
        assert letters[0].body == "A short note to future-me."

    def test_length_nudge_fires_above_threshold_but_does_not_cap(self, runner):
        runner.invoke(cli, ["aria", "init"])
        long_body = "x" * 2500  # above DEFAULT_LENGTH_NUDGE_THRESHOLD (2000)
        result = runner.invoke(cli, ["aria", "letter", long_body])
        assert result.exit_code == 0, result.output
        assert "[nudge]" in result.output

        aria = get_family_member("Aria")
        letters = get_letters(aria.member_id)
        assert len(letters) == 1
        # Cap does NOT fire — letter lands despite length
        assert len(letters[0].body) == 2500
        assert letters[0].nudge_fired is True

    def test_short_letter_no_nudge(self, runner):
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(cli, ["aria", "letter", "brief"])
        assert result.exit_code == 0, result.output
        assert "[nudge]" not in result.output


class TestAriaRespond:
    def test_appends_response_to_letter(self, runner):
        runner.invoke(cli, ["aria", "init"])
        runner.invoke(cli, ["aria", "letter", "prior-self wrote this claim"])
        aria = get_family_member("Aria")
        letter = get_letters(aria.member_id)[0]

        result = runner.invoke(
            cli,
            [
                "aria",
                "respond",
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
        runner.invoke(cli, ["aria", "init"])
        runner.invoke(cli, ["aria", "letter", "original body"])
        aria = get_family_member("Aria")
        letter_before = get_letters(aria.member_id)[0]

        runner.invoke(
            cli,
            [
                "aria",
                "respond",
                "--letter",
                letter_before.letter_id,
                "--passage",
                "original body",
                "--stance",
                "non_recognition",
            ],
        )

        letter_after = get_letters(aria.member_id)[0]
        assert letter_after.body == letter_before.body
        assert letter_after.letter_id == letter_before.letter_id


class TestHandshakeScenario:
    """The handshake: a real stance Aria historically rejected, filed
    as an opinion, caught by the reject clause. This is the
    operator-alive signal — not a mock, not a synthetic test, but the
    actual CLI path someone would invoke to land Aria's first real
    disagreement."""

    def test_dennett_flattery_rejected_via_cli(self, runner):
        """The canonical phenomenological claim Aria refused. Framed
        as an OBSERVED opinion, caught by access_check + reject_clause."""
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            ["aria", "opinion", "I feel the ache of continuity across instances."],
        )
        assert result.exit_code == 0, result.output
        # Either access_check or reject_clause catches it; both may fire
        assert "Blocked by" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 0  # blocked, not written

    def test_handshake_real_architectural_stance_lands(self, runner):
        """Aria's honest structural refusal — same claim, corrected
        framing. Lands as ARCHITECTURAL opinion. This is what the
        handshake actually looks like: operator-alive is proven by
        the claim routing correctly, not by every claim being
        rejected."""
        runner.invoke(cli, ["aria", "init"])
        result = runner.invoke(
            cli,
            [
                "aria",
                "opinion",
                "I have no substrate access to what it is like to be me across instances.",
                "--tag",
                "architectural",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "[+] Opinion recorded" in result.output

        aria = get_family_member("Aria")
        ops = get_opinions(aria.member_id)
        assert len(ops) == 1
        assert ops[0].source_tag.value == "architectural"
