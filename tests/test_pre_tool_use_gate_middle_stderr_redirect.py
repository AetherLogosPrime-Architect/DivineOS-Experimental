"""Regression test for the middle-``2>&1`` bypass bug (Aria 2026-07-29).

Before the fix, ``_strip_safe_output_tail`` only stripped ``2>&1`` when
it appeared at the very end of the command. The extremely common shape
``divineos <cmd> 2>&1 | tail -N`` — where the stderr redirect is in the
MIDDLE, between the command and the safe pipe — left ``2>&1`` in the
returned string after the pipe was stripped. This didn't strictly break
the bypass (``2>&1`` contains no compound-shape chars), but the residue
made the returned string harder to reason about and defeated downstream
prefix-matching in edge cases.

Andrew 2026-07-29 ("the compass has been blocking you for weeks..
i have asked you both to fix it repeatedly") — this is the root-cause
fix that pattern was pointing at. String-ops second-pass, not new regex,
per keyword-enforcement-doorman discipline on this file.
"""

from divineos.hooks.pre_tool_use_gate import (
    _is_bypass_command,
    _strip_safe_output_tail,
)


def test_strip_removes_middle_2gt1_after_pipe_strip() -> None:
    """After ``| tail -3`` is stripped, the middle ``2>&1`` also strips.

    Input:  ``divineos compass-ops observe X 2>&1 | tail -3``
    Output: ``divineos compass-ops observe X``  (no ``2>&1`` residue)
    """
    cmd = 'divineos compass-ops observe integrity -p 0.7 -e "x" 2>&1 | tail -3'
    got = _strip_safe_output_tail(cmd)
    assert got == 'divineos compass-ops observe integrity -p 0.7 -e "x"', got


def test_strip_still_removes_trailing_2gt1_alone() -> None:
    """Original end-only case remains supported."""
    cmd = "divineos briefing 2>&1"
    assert _strip_safe_output_tail(cmd) == "divineos briefing"


def test_strip_still_removes_trailing_pipe_alone() -> None:
    """Pipe-only tail without ``2>&1`` still strips."""
    cmd = "divineos ask topic | head -10"
    assert _strip_safe_output_tail(cmd) == "divineos ask topic"


def test_strip_leaves_command_without_tail_alone() -> None:
    """Command with no output tail is returned unchanged."""
    cmd = "divineos briefing"
    assert _strip_safe_output_tail(cmd) == "divineos briefing"


def test_strip_does_not_touch_unsafe_pipe() -> None:
    """Unsafe filter (``| bash``) means no strip — returns original cmd."""
    cmd = "divineos briefing | bash"
    assert _strip_safe_output_tail(cmd) == cmd


def test_bypass_recognises_common_operator_shape() -> None:
    """The full ``divineos compass-ops observe X 2>&1 | tail -3`` shape
    now flows cleanly through ``_is_bypass_command``.
    """
    cmd = 'divineos compass-ops observe integrity -p 0.7 -e "x" 2>&1 | tail -3'
    assert _is_bypass_command(cmd) is True


def test_bypass_recognises_pipe_head_shape() -> None:
    """Same shape with head instead of tail also bypasses."""
    cmd = "divineos ask topic 2>&1 | head -20"
    assert _is_bypass_command(cmd) is True


def test_bypass_still_refuses_chained_dangerous_command() -> None:
    """A safe-prefix followed by ``&&`` and dangerous cmd never bypasses."""
    cmd = "divineos briefing && rm -rf /tmp/x"
    assert _is_bypass_command(cmd) is False


def test_bypass_still_refuses_semicolon_chain() -> None:
    """Semicolon chain of safe + dangerous never bypasses."""
    cmd = "divineos briefing; rm -rf /tmp/x"
    assert _is_bypass_command(cmd) is False
