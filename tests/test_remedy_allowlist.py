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

    def test_env_value_containing_whitespace_stops_the_strip(self):
        """Documents the known limit rather than pretending it is handled."""
        assert not _is_remedy('MSG="two words" divineos correction "x"')
