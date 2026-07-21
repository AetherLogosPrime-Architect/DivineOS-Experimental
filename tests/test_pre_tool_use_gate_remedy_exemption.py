"""Regression tests for the Catch-22 fix in the remedy-exemption path.

The compass and correction gates each ship an exemption for their own
remedy commands (so the gate cannot block its own remedy — Aletheia
Finding 37 class). The exemption used a naive chain-shape regex that
was quote-blind: any semicolon inside a quoted argument tripped the
regex and denied the exemption, deadlocking the gate against its own
remedy.

Root fix (2026-07-21, council-2ad91226ebe7 schneier+popper+meadows):
factored the two duplicated exemption blocks into
`_is_safe_remedy_invocation()`, which uses shlex to distinguish shell-
metacharacters OUTSIDE quotes from ordinary punctuation inside quoted
argument text.

Test cases below are the Popper falsifiers named in the council walk.
All must pass before the fix is considered done.
"""

from __future__ import annotations

import pytest

from divineos.hooks.pre_tool_use_gate import (
    _has_unquoted_chain_shape,
    _is_safe_remedy_invocation,
)


class TestSemicolonInQuotedArg:
    """The exact Catch-22 shape: semicolon inside quoted arg must NOT
    trip the chain-shape check."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'divineos correction "text; with semi"',
            'divineos correction "gates never retired; only fixed"',
            'divineos learn "count first; verify after"',
            'divineos compass-ops observe integrity -e "reach was cheap; caught by architecture"',
        ],
    )
    def test_semicolon_in_quotes_is_safe(self, cmd: str) -> None:
        assert _has_unquoted_chain_shape(cmd) is False

    def test_correction_with_semicolon_arg_passes_exemption(self) -> None:
        cmd = 'divineos correction "text; with semi"'
        assert _is_safe_remedy_invocation(cmd, ("divineos correction", "divineos learn")) is True

    def test_compass_with_semicolon_arg_passes_exemption(self) -> None:
        cmd = 'divineos compass-ops observe integrity -e "a; b"'
        assert (
            _is_safe_remedy_invocation(
                cmd,
                ("divineos compass-ops observe", "divineos compass-ops dismiss"),
            )
            is True
        )


class TestRealChainAttacksStillRejected:
    """The threat model the chain-shape check protects (F22 hardening)
    must be preserved — unquoted chain metachars still reject."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'divineos correction "text" && rm -rf ~',
            'divineos correction "text"; rm -rf ~',
            'divineos correction "text" || echo pwned',
            'divineos correction "text" `whoami`',
            'divineos correction "text" $(whoami)',
        ],
    )
    def test_unquoted_chain_metachars_reject_exemption(self, cmd: str) -> None:
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is False


class TestPipeStillAllowed:
    """Pipe (|) is documented as still-allowed — the concrete use case
    that triggered the exemption is piping remedy output to head/tail."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'divineos correction "text" | tail -5',
            'divineos correction "text; semi" | tail -3',
            'divineos compass-ops observe integrity -e "x" | head -1',
        ],
    )
    def test_pipe_after_remedy_still_allowed(self, cmd: str) -> None:
        assert (
            _is_safe_remedy_invocation(
                cmd,
                (
                    "divineos correction",
                    "divineos compass-ops observe",
                    "divineos compass-ops dismiss",
                ),
            )
            is True
        )


class TestEscapeHatchScriptExempted:
    """The block message names clear_correction_marker.py as an escape
    hatch — the exemption list must include it."""

    @pytest.mark.parametrize(
        "cmd",
        [
            'python scripts/clear_correction_marker.py --reason "CLI was broken and I had a real correction to log"',
            'python scripts/clear_correction_marker.py --reason "text; with semi"',
        ],
    )
    def test_escape_hatch_script_passes_exemption(self, cmd: str) -> None:
        allowed = (
            "divineos learn",
            "divineos correction",
            "python scripts/clear_correction_marker.py",
        )
        assert _is_safe_remedy_invocation(cmd, allowed) is True


class TestMalformedFailsClosed:
    """Unclosed quote is malformed — MUST fail closed (return True from
    _has_unquoted_chain_shape, False from _is_safe_remedy_invocation)."""

    def test_unclosed_quote_fails_closed(self) -> None:
        cmd = 'divineos correction "unclosed'
        assert _has_unquoted_chain_shape(cmd) is True
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is False


class TestNonRemedyCommandsStillReject:
    """A command that is not one of the allowed heads must reject even
    if it has no chain-shape."""

    @pytest.mark.parametrize(
        "cmd",
        [
            "ls -la",
            "git status",
            'echo "harmless"',
            "python --version",
        ],
    )
    def test_non_remedy_rejects(self, cmd: str) -> None:
        assert _is_safe_remedy_invocation(cmd, ("divineos correction", "divineos learn")) is False


class TestEmptyCommand:
    """Empty command must reject (not accidentally allow via startswith
    on an empty prefix)."""

    def test_empty_string_rejects(self) -> None:
        assert _is_safe_remedy_invocation("", ("divineos correction",)) is False
