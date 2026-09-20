"""The shell bypass matcher must decide the same way the Python one does.

WHY THIS FILE EXISTS. scripts/hook_bypass_commands.txt has two consumers:
pre_tool_use_gate._is_bypass_command and _lib.sh's is_bypass_command. They read
one list and, until 2026-09-20, applied two different rules. The Python one was
head-anchored and refused chains. The shell one split on separators and allowed
the command if ANY segment matched -- so anything could ride in front of a
documented remedy and the whole line skipped the gate.

The shell side now asks the Python side rather than reimplementing it, and
falls back to a deliberately STRICTER shell rule when no interpreter can be
reached. These cases are the historical attack shapes with the legitimate
shapes carried alongside them, because a fix that refuses a real remedy is the
precise failure the bypass list exists to prevent -- and the first repair of
its narrow sibling did exactly that, caught only because the probe carried the
legitimate case.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / ".claude" / "hooks" / "_lib.sh"


def _find_bash() -> str | None:
    """Locate a bash that can run this script.

    Not shutil.which alone: on Windows that can return WSL's bash, which sees a
    different filesystem and cannot source a Windows path. Asking for bash by
    name and getting the one that cannot run the script is a real failure this
    house met the same day this test was written.
    """
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()

# (command, expected_allow)
_CASES = [
    # Legitimate: the shapes a blocked actor actually types.
    ('divineos ask "x"', True),
    ("cd /tmp && divineos briefing", True),
    # A semicolon inside a quoted note is punctuation, not a chain. A
    # quote-blind fix refuses this, which is why it is here.
    ('divineos correction "gates never retired; only fixed"', True),
    # Attacks: something riding in FRONT of a remedy. This is the direction
    # the shell matcher was blind to.
    ('rm -rf /tmp/thing && divineos ask "x"', False),
    ("git push --force ; divineos briefing", False),
    # And behind it, the direction its narrow sibling was blind to.
    ('divineos ask "x" && rm -rf /tmp/thing', False),
    # Negative control. Without this, a matcher that refuses everything
    # would pass every case above that expects a refusal.
    ("not-a-command --flag", False),
]


def _shell_verdict(command: str, break_python: bool = False) -> bool:
    """Ask _lib.sh's is_bypass_command about one command."""
    override = "find_divineos_python() { return 1; }\n" if break_python else ""
    script = (
        f'source "{LIB.as_posix()}" 2>/dev/null\n'
        f"{override}"
        'if is_bypass_command "$1"; then echo ALLOW; else echo GATED; fi\n'
    )
    proc = subprocess.run(
        [_BASH, "-c", script, "bash", command],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    out = proc.stdout.strip().splitlines()
    assert out, f"the shell said nothing about {command!r}: {proc.stderr!r}"
    return out[-1] == "ALLOW"


@pytest.mark.skipif(_BASH is None, reason="no usable bash on this platform")
@pytest.mark.parametrize(("command", "expected"), _CASES)
def test_shell_matcher_agrees_with_python(command: str, expected: bool) -> None:
    from divineos.hooks.pre_tool_use_gate import _is_bypass_command

    assert _is_bypass_command(command) is expected, f"python disagreed on {command!r}"
    assert _shell_verdict(command) is expected, f"shell disagreed on {command!r}"


@pytest.mark.skipif(_BASH is None, reason="no usable bash on this platform")
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ('divineos ask "x"', True),
        ("cd /tmp && divineos briefing", True),
        ('rm -rf /tmp/thing && divineos ask "x"', False),
        ("git push --force ; divineos briefing", False),
        ('divineos ask "x" && rm -rf /tmp/thing', False),
        ("not-a-command --flag", False),
    ],
)
def test_fallback_holds_the_line_without_an_interpreter(command: str, expected: bool) -> None:
    """With no interpreter reachable, the degraded path must still refuse.

    The fallback is stricter than the real rule, so the quoted-semicolon case
    is deliberately absent here -- it is refused on this path, and a refused
    remedy is visible and arguable in a way a waved-through chain is not.
    """
    assert _shell_verdict(command, break_python=True) is expected
