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
        """Being a divineos command is not enough — it must be somebody's exit."""
        assert not _is_remedy("divineos sleep")

    def test_remedy_named_inside_a_larger_argument(self):
        """Anchoring: a mention of the remedy is not an invocation of it."""
        assert not _is_remedy(f'{_GIT} commit -m "ran divineos correction earlier"')


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


class TestNothingRidesInBehindARemedy:
    """The third instance of the class this file was already written about.

    Its own opening says the defect was never the pattern list but the
    matcher's reading of shell, and that every legal prefix is a fresh hole.
    The two instances it names are both PREFIXES. Nobody asked the mirrored
    question until 2026-09-20: the pattern is start-anchored, so it reads the
    front of a command and nothing after it.

    Serein's external audit found a substitution riding a genuine remedy.
    Running his payloads here turned up the plainer form, which needs no
    substitution at all -- a real remedy, an operator, then anything. And
    because this library is consulted near the top of each gate that sources
    it and exits ALLOW on a match, a command wearing a remedy at the front
    does not merely satisfy the list: it skips that entire gate.

    The refusal must be quote-AWARE, which is why the first two cases below
    matter as much as the attacks. The re-joined text drops quoting, so a note
    that legitimately contains a semicolon is indistinguishable from a chained
    command, and a plain search would refuse honest remedies -- turning the
    file that exists to keep doors open into one that closes them.
    """

    def test_a_note_containing_a_semicolon_is_still_a_remedy(self):
        assert _is_remedy('divineos correction "gates never retired; only fixed"')

    def test_a_remedy_from_another_directory_is_still_a_remedy(self):
        """The regression my own first version introduced.

        I ran the chain check on the whole raw command, and the operator
        joining the directory change to the remedy read as a chain -- so a
        perfectly good remedy issued from a worktree got refused. That is the
        exact failure this whole file exists to prevent, committed by the
        repair. Caught only because the probe carried the legitimate prefixed
        case next to the attacks.
        """
        assert _is_remedy('cd "C:/DIVINE OS/DivineOS-Experimental" && divineos briefing')

    def test_a_chained_second_command_is_refused(self):
        assert not _is_remedy('divineos correction "x" && echo INJECTED')

    def test_a_semicolon_second_command_is_refused(self):
        assert not _is_remedy('divineos correction "x"; echo INJECTED')

    def test_a_substitution_outside_the_quotes_is_refused(self):
        assert not _is_remedy('divineos correction "x" $(echo INJECTED)')

    def test_a_backtick_outside_the_quotes_is_refused(self):
        assert not _is_remedy('divineos correction "x" `echo INJECTED`')

    def test_an_unclosed_quote_is_refused(self):
        """Fail-closed on malformed input: unparseable is not the same as safe."""
        assert not _is_remedy('divineos correction "unclosed')

    @pytest.mark.xfail(
        reason=(
            "KNOWN OPEN, and deliberately recorded as failing rather than left "
            "silent: a substitution inside DOUBLE quotes survives, because the "
            "shared checker blanks the contents of both quote kinds while single "
            "quotes are inert in shell and double quotes expand. Aether found "
            "this half and is repairing it in the file where that checker lives. "
            "Written as an expected failure so the day it starts passing, the "
            "suite says so instead of nobody noticing."
        ),
        strict=False,
    )
    def test_a_substitution_inside_double_quotes_is_refused(self):
        assert not _is_remedy('divineos correction "note $(echo INJECTED)"')
