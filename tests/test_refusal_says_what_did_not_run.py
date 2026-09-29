"""A refusal must say what did NOT run, when the line it refused had halves.

The fault in one sentence: a gate refuses a compound line, its message names
the clause that tripped it, and the reader infers the fate of the other
clauses. Twice in one week that inference cost real work -- thirty letters one
day, a branch whose diff against main was empty the next.

PROVENANCE OF THE FIXTURES, because the neighbouring test file taught me to
declare it and the omission would be the same class of quiet wrongness these
tests exist to catch. The lines in TestTheRealFaultsThatProducedThis are
RECONSTRUCTED FROM THE LETTERS that reported each incident, not copied from a
shell record. They carry the right SHAPE -- a joiner with work on both sides --
which is the only property under test here. They are not claims about the exact
bytes anybody typed. The genuine 2026-09-04 line is kept verbatim next door in
test_a_refused_line_drops_its_unrun_half.py, where its exact form is load-
bearing; here it would only be decoration borrowed to look authoritative.

Written against the SHAPE of the message rather than its wording, except for
the claims that are load-bearing and must not soften: that nothing ran, that
clauses on BOTH sides died, and that the whole line is what to re-issue.
"""

from __future__ import annotations

import pytest

from divineos.hooks import pre_tool_use_gate as gate


class TestFooterFiresOnTheLinesThatCanBeBisected:
    """A line with clauses gets the footer; a single command does not."""

    @pytest.mark.parametrize(
        "command",
        [
            "git commit -m 'x' && git push",
            "git checkout main; git rm foo",
            "git fetch || echo failed",
            "git add .\ngit commit -m 'x'",
        ],
    )
    def test_a_joined_line_is_told_that_nothing_ran(self, command: str) -> None:
        assert gate._nothing_ran_footer(command), f"no footer for: {command!r}"

    @pytest.mark.parametrize("command", ["git push", "ls -la", "pytest tests/ -q", ""])
    def test_a_single_command_gets_no_wallpaper(self, command: str) -> None:
        """True there too, and printing it every time is how a footer dies unread."""
        assert gate._nothing_ran_footer(command) == ""


class TestTheThreeClaimsThatMustNotSoften:
    """Each was bought with real work and none is decoration."""

    def test_it_says_nothing_ran_without_hedging(self) -> None:
        """Aether's correction to the first draft: 'may not have run' invites
        the reader to reconstruct a hopeful half, which is the exact inference
        that cost him the branch. These gates fire before the shell.
        """
        footer = gate._nothing_ran_footer("a && b").lower()
        assert "nothing on this line ran" in footer
        assert "no clause executed" in footer
        for hedge in ("may not have run", "might not have run", "possibly"):
            assert hedge not in footer, f"the claim was hedged with {hedge!r}"

    def test_it_says_to_re_issue_the_whole_line(self) -> None:
        """The half that actually saves the work.

        Misreading a refusal is survivable alone. Re-running one FRAGMENT is
        what executed in a state the full line would have established and did
        not -- both times, in both directions.
        """
        footer = gate._nothing_ran_footer("a && b").lower()
        assert "whole line" in footer
        assert "fragment" in footer

    def test_it_names_the_clauses_before_as_well_as_after(self) -> None:
        """The thirty-letter loss was a dropped clause BEFORE the named one.

        A message promising only about what came after would have been
        accurate for the empty-branch case and useless for the letters case,
        while reading as though it covered both.
        """
        assert "before" in gate._nothing_ran_footer("a && b").lower()


class TestItReachesARealRefusal:
    """The footer is worthless if it never arrives attached to a deny."""

    def test_a_deny_carries_the_footer_for_a_joined_line(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(gate, "_REFUSED_COMMAND", "git commit -m 'x' && git push")
        reason = gate._make_deny("BLOCKED: something objected")["hookSpecificOutput"][
            "permissionDecisionReason"
        ]
        assert reason.startswith("BLOCKED: something objected")
        assert "nothing on this line ran" in reason.lower()

    def test_a_deny_for_a_single_command_is_left_alone(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(gate, "_REFUSED_COMMAND", "git push")
        reason = gate._make_deny("BLOCKED: something objected")["hookSpecificOutput"][
            "permissionDecisionReason"
        ]
        assert reason == "BLOCKED: something objected"

    def test_an_unset_command_does_not_break_the_refusal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A gate refusing a non-Bash tool has no command and must still refuse.

        Fail-soft in the only safe direction: the refusal must survive, the
        footer is the part allowed to be absent.
        """
        monkeypatch.setattr(gate, "_REFUSED_COMMAND", "")
        reason = gate._make_deny("BLOCKED: something objected")["hookSpecificOutput"][
            "permissionDecisionReason"
        ]
        assert reason == "BLOCKED: something objected"


class TestTheRealFaultsThatProducedThis:
    """Both incidents as executable cases. Fixtures reconstructed -- see module
    docstring; the shape is what is under test, not the bytes."""

    def test_the_commit_and_push_line(self) -> None:
        """2026-09-05: refusal named the push, the commit never ran, diff empty."""
        assert gate._nothing_ran_footer("git commit -am 'fix' && git push origin head")

    def test_the_switch_and_remove_line(self) -> None:
        """2026-09-04: refusal named the removal, the switch never ran, wrong branch."""
        assert gate._nothing_ran_footer("git checkout code-branch && git rm -r letters/")
