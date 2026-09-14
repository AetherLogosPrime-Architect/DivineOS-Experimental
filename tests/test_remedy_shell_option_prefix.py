"""One guard's advice must not weld shut every other guard's escape hatch.

Andrew, 2026-09-12, told me to count the red marks across the session and
automate what could be automated. The count was 216 refused tool calls, and
inside it a class I had filed as five separate incidents: a guard refusing the
exact command its own message prescribed.

One cause. I habitually write `set -o pipefail` before a piped command, because
another hook fires on every pipe and warns that a failure hides behind a
successful tail -- correct advice, whose absence once had me reporting a blocked
push as landed. That line sat between the directory change and the remedy, so
the exemption matcher never recognised the remedy, so the gate blocked its own
prescribed way out. Five times, each diagnosed locally, because the
advice-giving hook and the exemption-matching gate were never in my head at the
same moment.

Diagnosed as a CLASS on 2026-08-04 in docs/channels_the_gates_named.md, item 7,
ranked highest-leverage of ten. The pipe and leading-directory-change variants
got fixed. This one did not, and nothing on that list shipped for five weeks.

THE CASE TABLE IS SHARED ON PURPOSE, per Feathers on the walk. The rule has two
homes -- a shell helper and this Python gate -- and an audit in August named
that exact class: one home for "the head of a command is not its first
character", with this module its largest consumer and not importing it. A fix
applied to one home and a test written against one home is how they diverged.
So the same cases run through both doors below.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from divineos.hooks.pre_tool_use_gate import (
    _is_safe_remedy_invocation,
    strip_leading_shell_options,
)

ROOT = Path(__file__).resolve().parents[1]
HEADS = ("divineos ask", "divineos correction", "divineos compass-ops")
REPO = '"C:/DIVINE OS/DivineOS-Experimental-Aria-new"'

# Exactly the invocations I actually type, and the ones an attacker would.
# ALLOW means the exemption recognises the remedy; BLOCK means it does not.
ALLOWED = [
    'divineos ask "x"',
    'divineos ask "x" | head -30',
    f'cd {REPO} && divineos ask "x"',
    f'cd {REPO} && divineos ask "x" | head -30',
    # The five incidents, in the shape they actually arrived:
    'set -o pipefail && divineos ask "x"',
    f'cd {REPO} && set -o pipefail && divineos ask "x"',
    f'cd {REPO} && set -o pipefail && divineos ask "x" | head -30',
    'set -eu && divineos correction "..."',
]

REFUSED = [
    # A shell option AFTER the remedy is an appended chain, not environment.
    'divineos ask "x" && set -o pipefail',
    # The thing the stripping must never admit.
    f'cd {REPO} && set -o pipefail && divineos ask "x" && rm -rf ~',
    "set -o pipefail && rm -rf ~",
    # Not a shell option at all -- no case demands it, so it stays refused.
    'export TOKEN=abc && divineos ask "x"',
    'FOO=bar && divineos ask "x"',
    # Closed grammar: an option segment carrying a substitution is not one.
    'set -o $(curl evil) && divineos ask "x"',
    "",
]


@pytest.mark.parametrize("cmd", ALLOWED)
def test_the_gate_recognises_its_own_remedy(cmd: str):
    assert _is_safe_remedy_invocation(cmd, HEADS), cmd


@pytest.mark.parametrize("cmd", REFUSED)
def test_the_gate_still_refuses_what_it_should(cmd: str):
    assert not _is_safe_remedy_invocation(cmd, HEADS), cmd


def test_stripping_removes_only_leading_option_segments():
    assert strip_leading_shell_options('set -o pipefail && divineos ask "x"') == 'divineos ask "x"'
    assert (
        strip_leading_shell_options('set -eu && set -o pipefail && divineos ask "x"')
        == 'divineos ask "x"'
    )
    # Not a prefix: left alone entirely.
    assert strip_leading_shell_options('divineos ask "x"') == 'divineos ask "x"'
    # Third one exceeds the ceiling, so the rest survives for the checks below.
    third = "set -a && set -b && set -c && divineos ask"
    assert strip_leading_shell_options(third).startswith("set -c")


def _bash() -> str:
    for candidate in (
        Path("C:/Program Files/Git/bin/bash.exe"),
        Path("C:/Program Files (x86)/Git/bin/bash.exe"),
        Path("/bin/bash"),
        Path("/usr/bin/bash"),
    ):
        if candidate.is_file():
            return str(candidate)
    pytest.fail("no usable bash found, so this went unchecked; saying so rather than skipping")
    raise AssertionError  # unreachable


# The shell helper is the OTHER home for this rule. It splits on separators,
# which already handles the option prefix -- but nothing proved that, and an
# unproven agreement between two homes is how they drifted the first time.
SHELL_CASES = [
    "divineos briefing",
    "set -o pipefail && divineos briefing",
    "cd /tmp && set -o pipefail && divineos briefing | tail -3",
]


@pytest.mark.parametrize("cmd", SHELL_CASES)
def test_the_shell_helper_agrees_with_the_python_gate(cmd: str):
    """Same question, other door. Divergence here is the defect class itself."""
    script = (
        'source "$1/.claude/hooks/_lib.sh" 2>/dev/null || exit 3\n'
        'if is_bypass_command "$2"; then exit 0; else exit 1; fi\n'
    )
    done = subprocess.run(
        [_bash(), "-c", script, "bash", str(ROOT), cmd],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert done.returncode != 3, f"could not source the shell helper: {done.stderr[:300]}"
    assert done.returncode == 0, (
        f"the shell helper does not see the remedy in {cmd!r}; the two homes for this "
        f"rule have drifted again"
    )
