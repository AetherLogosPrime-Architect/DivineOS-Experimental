"""No gate may block another gate's prescribed way out.

Andrew 2026-08-18: *"no gate should ever be blocking its own remedy."*

The deadlock this ends was measured, not imagined: a closed cycle where all
four named exits from one marker were each held shut by a different gate, and
the only way through was the fire door -- which is for a burning building
rather than a Tuesday. Bypass habituation degrades a gate to a warning, so a
deadlock that forces the fire door on an ordinary day is a slow way of killing
every gate at once.

THE SAFETY PROPERTY IS TESTED, NOT TRUSTED. This list can only ever let
something through, so the question that matters is what it can let through. A
test asserting no dangerous verb can ever appear is the thing standing between
an anti-deadlock measure and a way around the gates -- and it must not depend
on my remembering the rule when I next edit the list.
"""

from __future__ import annotations

from divineos.core import hook_router as hr
from divineos.core.hook_router import SurfaceOutcome
from divineos.core.remedy_allowlist import FORBIDDEN_HEADS, REMEDIES, is_remedy


class TestWhatCounts:
    def test_the_prescribed_exits_are_recognised(self):
        for command in (
            'divineos correction "x"',
            'divineos learn "x"',
            'divineos reach open "t"',
            "divineos goal add x",
            "divineos compass-ops observe TRUTHFULNESS -p 0",
            "divineos prereg assess p1 --outcome FAILED",
        ):
            assert is_remedy(command), command

    def test_wrapping_and_assignment_prefixes_do_not_hide_a_remedy(self):
        """Three separate times the shell version re-opened the deadlock this
        way -- a worktree prefix, then an environment assignment -- because its
        pattern was anchored to the start of a raw string. Its own final note
        says the answer is to parse rather than add another loop, and that is
        what this does."""
        assert is_remedy('cd /some/worktree && divineos correction "x"')
        assert is_remedy('MSG="two words" divineos correction "x"')
        assert is_remedy("DIVINEOS_SOMETHING=1 divineos compass-ops observe X -p 0")

    def test_ordinary_work_is_not_a_remedy(self):
        for command in ("git push origin main", "pytest tests/ -q", "ls -la", ""):
            assert not is_remedy(command), command

    def test_a_near_miss_is_not_a_remedy(self):
        """Token matching, not substring: a longer word starting with a remedy
        name must not slip through."""
        assert not is_remedy("divineos correctionsomething")
        assert is_remedy("divineos correction x")  # control

    def test_filing_a_new_prereg_is_deliberately_not_a_remedy(self):
        """Only the two commands that CLEAR the overdue gate belong here.
        Filing a new one is ordinary substrate writing and nobody's exit."""
        assert not is_remedy('divineos prereg file "a new claim"')
        assert is_remedy("divineos prereg assess p1 --outcome SUCCESS")


class TestItCannotBecomeAWayAround:
    def test_no_dangerous_verb_can_ever_be_on_the_list(self):
        """The safety property, asserted rather than remembered.

        Everything here must be a RECORDING action. If a version-control,
        test, deletion or editing command ever appears, this has stopped being
        an anti-deadlock measure and become a hole.
        """
        for prefix in REMEDIES:
            assert prefix[0] not in FORBIDDEN_HEADS, prefix
            assert prefix[0] == "divineos", f"only substrate commands belong here: {prefix}"

    def test_the_forbidden_set_actually_contains_the_dangerous_verbs(self):
        """Control for the test above. Without this, emptying the forbidden set
        would make that assertion pass trivially."""
        for verb in ("git", "gh", "rm", "pytest"):
            assert verb in FORBIDDEN_HEADS


class TestTheRouterStandsAside:
    def setup_method(self):
        hr.clear("PreToolUse")
        hr.register(
            "PreToolUse",
            "always_refuses",
            lambda p: SurfaceOutcome(name="always_refuses", refused=True, reason="NO"),
        )

    def teardown_method(self):
        hr.clear("PreToolUse")

    def test_an_ordinary_command_is_still_refused(self):
        """The control, and it comes first on purpose: if this ever passes
        trivially, the allowlist has disarmed the gate rather than scoped it."""
        result = hr.dispatch(
            "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "git push"}}
        )
        assert result.blocked is True
        assert result.exit_code() == 2

    def test_a_prescribed_remedy_is_not_refused(self):
        result = hr.dispatch(
            "PreToolUse",
            {"tool_name": "Bash", "tool_input": {"command": 'divineos correction "x"'}},
        )
        assert result.blocked is False
        assert result.exit_code() == 0

    def test_the_standing_aside_is_announced_rather_than_silent(self):
        """A silent allowlist rots into an unexamined hole. The gate's claim
        was not wrong -- it simply may not stand in front of another gate's
        remedy -- so it is downgraded to a report, not deleted."""
        result = hr.dispatch(
            "PreToolUse",
            {"tool_name": "Bash", "tool_input": {"command": 'divineos correction "x"'}},
        )
        said = result.stdout()
        assert "always_refuses" in said
        assert "stands aside" in said

    def test_only_bash_commands_are_considered(self):
        """A remedy is a COMMAND. An edit that happens to contain the same text
        is not somebody's way out, and must not be waved through."""
        result = hr.dispatch(
            "PreToolUse",
            {"tool_name": "Edit", "tool_input": {"new_string": 'divineos correction "x"'}},
        )
        assert result.blocked is True

    def test_other_doors_are_untouched(self):
        """Only the door where gates refuse commands needs this. Applying it
        anywhere else would be scope creep dressed as consistency."""
        hr.clear("Stop")
        hr.register(
            "Stop",
            "stop_refuses",
            lambda p: SurfaceOutcome(name="stop_refuses", refused=True, reason="NO"),
        )
        result = hr.dispatch(
            "Stop", {"tool_name": "Bash", "tool_input": {"command": 'divineos correction "x"'}}
        )
        assert result.blocked is True
        hr.clear("Stop")
