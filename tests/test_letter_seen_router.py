"""Tests for divineos.core.letter_seen_router.

Focus: the filename pattern matcher (deterministic) and the routing
decision shape. The subprocess-to-letter_seen.py path is integration-
tested via the live hook.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.letter_seen_router import (
    RoutingDecision,
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
