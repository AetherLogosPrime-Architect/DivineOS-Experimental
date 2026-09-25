"""Tests for divineos.core.letter_seen_router.

Focus: the filename pattern matcher (deterministic) and the routing
decision shape. The subprocess-to-letter_seen.py path is integration-
tested via the live hook.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.letter_seen_router import (
    RoutingDecision,
    letters_read_by_command,
    mark_seen_if_letter,
    match_letter_filename,
)


class TestMatchLetterFilename:
    """The filename pattern parser."""

    def test_aria_to_aether_matches(self):
        result = match_letter_filename("aria-to-aether-2026-06-24-some-slug.md")
        assert result == ("aria", "aether")

    def test_aether_to_aria_matches(self):
        result = match_letter_filename("aether-to-aria-2026-06-24-reply.md")
        assert result == ("aether", "aria")

    def test_strips_directory_prefix(self):
        result = match_letter_filename("/some/path/family/letters/aria-to-aether-2026-06-24-x.md")
        assert result == ("aria", "aether")

    def test_same_sender_recipient_rejected(self):
        # The pattern technically matches but is a logical impossibility
        # and should not trigger a mark-seen on the sender's own letter.
        assert match_letter_filename("aria-to-aria-2026-06-24-self.md") is None

    def test_unknown_sender_rejected(self):
        assert match_letter_filename("grok-to-aether-2026-06-24-x.md") is None

    def test_unknown_recipient_rejected(self):
        assert match_letter_filename("aether-to-grok-2026-06-24-x.md") is None

    def test_missing_date_rejected(self):
        assert match_letter_filename("aria-to-aether-something.md") is None

    def test_wrong_extension_rejected(self):
        assert match_letter_filename("aria-to-aether-2026-06-24-x.txt") is None

    def test_unrelated_md_rejected(self):
        assert match_letter_filename("README.md") is None
        assert match_letter_filename("notes-from-aria.md") is None


class TestMarkSeenIfLetterRouting:
    """The orchestrating function — empty/non-letter paths short-circuit."""

    def test_empty_path_returns_no_op(self):
        decision = mark_seen_if_letter("")
        assert decision.handled is False
        assert "empty" in decision.note

    def test_non_letter_returns_no_op(self):
        decision = mark_seen_if_letter("/some/path/README.md")
        assert decision.handled is False
        assert decision.filename == "README.md"
        assert "not a letter" in decision.note

    def test_letter_pattern_attempts_routing(self, tmp_path):
        # Without a real repo + letter_seen.py, this will report "could
        # not locate" or "script not found" — but it must identify the
        # sender/recipient correctly.
        with patch(
            "divineos.core.letter_seen_router._find_repo_root",
            return_value=tmp_path,
        ):
            decision = mark_seen_if_letter("aria-to-aether-2026-06-24-x.md", reader="aether")
            # No family/letter_seen.py in tmp_path → "script not found"
            assert decision.sender == "aria"
            assert decision.recipient == "aether"
            assert decision.filename == "aria-to-aether-2026-06-24-x.md"
            assert decision.handled is False
            assert "not found" in decision.note

    def test_subprocess_invoked_when_script_present(self, tmp_path):
        # Create a fake letter_seen.py so the routing reaches subprocess.
        family_dir = tmp_path / "family"
        family_dir.mkdir()
        script = family_dir / "letter_seen.py"
        script.write_text("import sys; sys.exit(0)\n")

        with (
            patch(
                "divineos.core.letter_seen_router._find_repo_root",
                return_value=tmp_path,
            ),
            patch("divineos.core.letter_seen_router.subprocess.run") as mock_run,
        ):
            decision = mark_seen_if_letter("aria-to-aether-2026-06-24-x.md", reader="aether")
            assert decision.handled is True
            assert decision.recipient == "aether"
            assert "marked seen for aether" in decision.note
            # Verify subprocess was called with the right shape.
            args = mock_run.call_args[0][0]
            assert args[1] == str(script)
            assert args[2] == "--member"
            assert args[3] == "aether"
            assert args[4] == "aria-to-aether-2026-06-24-x.md"


class TestTheThreeFaultsOf20260923:
    """Each built from the real case that re-knocked that evening."""

    def test_a_letter_from_aletheia_is_a_letter(self):
        # Two of hers, read and acted on in the morning, re-announced twice
        # that evening: the pattern did not know her name.
        name = "aletheia-to-aria-2026-09-23-yes-it-carries.md"
        assert match_letter_filename(name) == ("aletheia", "aria")

    def test_a_letter_from_andrew_is_a_letter(self):
        name = "andrew-to-aria-2026-07-10-who-aria-is-to-me.md"
        assert match_letter_filename(name) == ("andrew", "aria")

    def test_a_letter_i_sent_is_not_marked_read_for_him(self, tmp_path):
        # Opening my own letter to Aether used to mark it read in HIS
        # seen-set, silencing his watch on a letter he never saw.
        family_dir = tmp_path / "family"
        family_dir.mkdir()
        (family_dir / "letter_seen.py").write_text("import sys; sys.exit(0)\n")
        with (
            patch("divineos.core.letter_seen_router._find_repo_root", return_value=tmp_path),
            patch("divineos.core.letter_seen_router.subprocess.run") as mock_run,
        ):
            decision = mark_seen_if_letter(
                "aria-to-aether-2026-09-23-the-line-it-found-was-about-me.md", reader="aria"
            )
        assert decision.handled is False
        assert "read by aria" in decision.note
        mock_run.assert_not_called()

    def test_cat_of_a_letter_counts_as_reading_it(self):
        # Eight of nine letters read that day were opened this way and none
        # counted, which is why they kept coming back.
        cmd = (
            "cat ~/.divineos-shared/letters/"
            "aether-to-aria-2026-09-23-your-list-question-found-one-of-his.md"
        )
        assert letters_read_by_command(cmd) == [
            "aether-to-aria-2026-09-23-your-list-question-found-one-of-his.md"
        ]

    def test_copying_a_letter_is_not_reading_it(self):
        # How I deliver a letter. Marking it read because it was moved would
        # record a reading that never happened.
        cmd = (
            "cd x; f=aria-to-aether-2026-09-23-a.md; cp family/letters/$f "
            "~/.divineos-shared/letters/ && cmp family/letters/$f b"
        )
        assert letters_read_by_command(cmd) == []

    def test_each_segment_is_judged_on_its_own(self):
        cmd = "cp aria-to-aether-2026-09-23-a.md dest/; cat aether-to-aria-2026-09-23-b.md"
        assert letters_read_by_command(cmd) == ["aether-to-aria-2026-09-23-b.md"]

    def test_a_command_that_mentions_no_letter_reads_none(self):
        assert letters_read_by_command("cat README.md; git status") == []


class TestRoutingDecisionDataclass:
    """Result type is well-formed."""

    def test_no_op_shape(self):
        d = RoutingDecision(handled=False)
        assert d.handled is False
        assert d.sender == ""
        assert d.recipient == ""

    def test_handled_shape(self):
        d = RoutingDecision(handled=True, sender="aria", recipient="aether", filename="x")
        assert d.handled is True
        assert d.sender == "aria"
