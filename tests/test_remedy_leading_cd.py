"""A remedy command must stay exempt behind a leading `cd <path> &&`.

Aria 2026-08-01, confirmed by controlled test rather than argued.

The gate's block message names two ways out: file the correction, or clear
the marker. Both are remedy commands. The exemption required the remedy to
be the FIRST token, so a habitual `cd "<repo>" && divineos correction "..."`
put `cd` in head position and the exemption missed — the gate blocked the
exact command it had just instructed. Neither exit worked; the deadlock was
total.

I hypothesised this hours before proving it and then withdrew it untested,
because the next attempt hit a DIFFERENT gate stacked behind this one and I
read that as disproof (correction #80). The confirming experiment was one
command with the prefix removed. Controls are cheap; retracting a correct
diagnosis is not.

These tests pin both halves: the prefix must not defeat the exemption, and
stripping it must not open a chain-injection path.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import (
    _is_safe_remedy_invocation,
    _strip_leading_cd,
)

HEADS = ("divineos correction", "python scripts/clear_correction_marker.py")


class TestLeadingCdStripped:
    def test_the_exact_deadlock_command(self) -> None:
        """The literal shape that blocked me. Regression anchor."""
        cmd = 'cd "C:/DIVINE OS/DivineOS-Experimental-Aria-new" && divineos correction "x"'
        assert _is_safe_remedy_invocation(cmd, HEADS)

    def test_bare_remedy_still_exempt(self) -> None:
        assert _is_safe_remedy_invocation('divineos correction "x"', HEADS)

    @pytest.mark.parametrize(
        "prefix",
        ['cd "/a b/c" && ', "cd '/a b/c' && ", "cd /tmp && ", "  cd /tmp   &&   "],
    )
    def test_quoting_and_spacing_variants(self, prefix: str) -> None:
        assert _is_safe_remedy_invocation(prefix + 'divineos correction "x"', HEADS)

    def test_pipe_after_remedy_still_allowed(self) -> None:
        cmd = 'cd /tmp && divineos correction "x" | tail -3'
        assert _is_safe_remedy_invocation(cmd, HEADS)


class TestStripDoesNotWidenTheSurface:
    def test_appended_chain_still_refused(self) -> None:
        """The whole point: stripping cd must not let a chain through."""
        cmd = 'cd /tmp && divineos correction "x" && rm -rf ~'
        assert not _is_safe_remedy_invocation(cmd, HEADS)

    def test_only_one_cd_is_stripped(self) -> None:
        """Second cd stays in head position, so the head-check still fails."""
        cmd = 'cd /a && cd /b && divineos correction "x"'
        assert not _is_safe_remedy_invocation(cmd, HEADS)

    @pytest.mark.parametrize(
        "path",
        ["/tmp;rm", "/tmp&&rm", "$(whoami)", "`whoami`", "/tmp|rm", "/tmp>out"],
    )
    def test_metachar_paths_are_not_stripped(self, path: str) -> None:
        """A path carrying metachars is left in place, not quietly removed."""
        cmd = f'cd {path} && divineos correction "x"'
        assert _strip_leading_cd(cmd) == cmd
        assert not _is_safe_remedy_invocation(cmd, HEADS)

    def test_non_remedy_behind_cd_is_still_refused(self) -> None:
        cmd = "cd /tmp && rm -rf ~"
        assert not _is_safe_remedy_invocation(cmd, HEADS)

    def test_cd_alone_is_not_a_remedy(self) -> None:
        assert not _is_safe_remedy_invocation("cd /tmp", HEADS)


class TestStripIsInert:
    def test_no_cd_leaves_command_untouched(self) -> None:
        cmd = 'divineos correction "cd /tmp && something in the text"'
        assert _strip_leading_cd(cmd) == cmd

    def test_quoted_text_mentioning_cd_survives(self) -> None:
        """A correction ABOUT this bug must not be mangled by the fix."""
        cmd = 'divineos correction "the cd prefix && defeated the exemption"'
        assert _is_safe_remedy_invocation(cmd, HEADS)

    def test_empty_is_false(self) -> None:
        assert not _is_safe_remedy_invocation("", HEADS)
