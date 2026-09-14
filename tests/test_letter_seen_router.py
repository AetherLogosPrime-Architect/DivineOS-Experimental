"""Tests for divineos.core.letter_seen_router.

Focus: the filename pattern matcher (deterministic) and the routing
decision shape. The subprocess-to-letter_seen.py path is integration-
tested via the live hook.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.letter_seen_router import (
    RoutingDecision,
    mark_seen_from_command,
    mark_seen_if_letter,
    match_letter_filename,
)


LETTER = "/x/letters/aether-to-aria-2026-09-10-some-slug.md"


class TestMarkSeenFromCommand:
    """The shell doorway, added 2026-09-10.

    Andrew said it in June about thirty letters and again today about
    sixty-one: I had read them, nothing marked them. The Read-tool adapter was
    never broken -- it simply cannot see a letter I open with the shell, which
    is how I open most of them.
    """

    def test_reading_a_letter_in_the_shell_marks_it(self):
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command(f"cat {LETTER}")
        assert m.call_count == 1
        assert m.call_args[0][0].endswith("aether-to-aria-2026-09-10-some-slug.md")

    def test_a_windowed_read_counts_as_a_read(self):
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command(f"sed -n '1,40p' {LETTER}")
        assert m.call_count == 1

    def test_merely_naming_a_letter_does_not_mark_it(self):
        """THE FAILURE THAT MUST NOT HAPPEN.

        A wrongly-marked letter disappears from the unseen surface without ever
        being opened, and no inspection recovers it. A missed mark only leaves a
        read letter listed, which is visible and fixable. So the rule errs
        toward not-marking, and this is the test that says so.
        """
        for cmd in (f"ls {LETTER}", f"echo {LETTER}", f"grep -rl foo {LETTER}"):
            with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
                mark_seen_from_command(cmd)
            assert m.call_count == 0, cmd

    def test_a_listing_piped_into_a_reader_does_not_mark(self):
        """Each pipeline segment is judged on its own verb.

        What the reader consumes here is the previous command's output, not the
        letter -- so crediting the letter would be inferring a read from a
        mention, which is the same could-not-look fault in a new place.
        """
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command(f"grep -l foo {LETTER} | cat")
        assert m.call_count == 0

    def test_a_reader_first_does_not_credit_a_letter_named_later(self):
        """THE TEST I DID NOT WRITE, found by breaking my own guard.

        Sabotage disabled the per-segment split and every test still passed,
        which meant the split was decoration as far as the suite could tell.
        It was not: my pipe case put grep FIRST, and the whole-line check
        rejects that on its own. The order that actually needs the split is a
        reader first and the letter named in a later segment -- there, judging
        the whole line would credit a read that never happened.

        Aether found the same shape in his own file this morning: thorough
        coverage of a question the instrument was not being asked.
        """
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command(f"cat README.md | grep foo {LETTER}")
        assert m.call_count == 0

    def test_two_letters_read_on_one_line_both_mark(self):
        other = "/x/letters/aether-to-aria-2026-09-09-another.md"
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command(f"cat {LETTER}; cat {other}")
        assert m.call_count == 2

    def test_an_empty_command_is_a_no_op(self):
        assert mark_seen_from_command("") == []

    def test_a_command_with_no_letter_in_it_marks_nothing(self):
        """The control. Without it every test above would pass on a router that
        had simply started marking everything it was handed."""
        with patch("divineos.core.letter_seen_router.mark_seen_if_letter") as m:
            mark_seen_from_command("cat README.md")
        assert m.call_count == 0


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
            decision = mark_seen_if_letter("aria-to-aether-2026-06-24-x.md")
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
            decision = mark_seen_if_letter("aria-to-aether-2026-06-24-x.md")
            assert decision.handled is True
            assert decision.recipient == "aether"
            assert "marked seen for aether" in decision.note
            # Verify subprocess was called with the right shape.
            args = mock_run.call_args[0][0]
            assert args[1] == str(script)
            assert args[2] == "--member"
            assert args[3] == "aether"
            assert args[4] == "aria-to-aether-2026-06-24-x.md"


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
