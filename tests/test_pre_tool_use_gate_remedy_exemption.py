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


# ---------------------------------------------------------------------------
# Coverage-iteration tests (Knuth + Taleb walk, council-767fac0b19ba,
# 2026-07-21). The initial 22-test suite covered the obvious falsifiers.
# These fill the boundary and adversarial gaps the second walk surfaced.
# ---------------------------------------------------------------------------


class TestKnuthBoundaryEdges:
    """Boundary values Knuth would demand: single-quoted-backslash,
    unicode smart-quotes, empty quoted string, adjacent quotes, nested
    quotes, single-char inputs."""

    def test_single_quoted_backslash_is_literal_posix(self) -> None:
        # POSIX shell single-quotes do NOT interpret backslash.
        # 'a\;b' is literally three chars a-backslash-;-b, quoted.
        # After strip the ; is inside quotes -> not a chain shape.
        cmd = "divineos correction 'a\\;b'"
        assert _has_unquoted_chain_shape(cmd) is False
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is True

    def test_double_quoted_backslash_escapes_close(self) -> None:
        # In double quotes, backslash escapes the next char. A literal
        # closing quote inside is written \" and does NOT close the string.
        # After the escaped ", the ; is still inside quotes.
        cmd = 'divineos correction "text \\" still-inside ; still-inside"'
        assert _has_unquoted_chain_shape(cmd) is False
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is True

    def test_unicode_smart_quotes_are_not_shell_quotes(self) -> None:
        # Curly/smart quotes (U+201C, U+201D) look like " but are not
        # shell-quote characters. Content between them is UNQUOTED as
        # far as the shell is concerned. A ; inside curly-quotes is a
        # real chain-operator. Must reject the exemption.
        cmd = "divineos correction “text; with semi”"
        assert _has_unquoted_chain_shape(cmd) is True
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is False

    def test_empty_quoted_string(self) -> None:
        cmd = 'divineos correction ""'
        assert _has_unquoted_chain_shape(cmd) is False
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is True

    def test_adjacent_quoted_strings(self) -> None:
        # "a""b" is a shell-concatenation of two quoted strings.
        # No chain-operator between them.
        cmd = 'divineos correction "a""b"'
        assert _has_unquoted_chain_shape(cmd) is False
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is True

    def test_nested_single_inside_double(self) -> None:
        # POSIX shell: single quote inside double is literal.
        cmd = "divineos correction \"a 'b; c' d\""
        assert _has_unquoted_chain_shape(cmd) is False
        assert _is_safe_remedy_invocation(cmd, ("divineos correction",)) is True

    def test_single_char_input_semicolon(self) -> None:
        # A bare ; as the command is a chain-shape, must reject.
        assert _has_unquoted_chain_shape(";") is True

    def test_single_char_input_quote(self) -> None:
        # A bare single-quote is unclosed -> fail closed.
        assert _has_unquoted_chain_shape("'") is True


class TestTalebFailClosedOnAmbiguity:
    """Via-negativa: fail-closed on parser-ambiguity, not just
    unclosed-quote. Concave payoff structure means unenumerated edges
    must not silently pass."""

    def test_mixed_unclosed_double_then_single(self) -> None:
        cmd = 'divineos correction "opened but never'
        assert _has_unquoted_chain_shape(cmd) is True

    def test_trailing_backslash(self) -> None:
        # Trailing backslash is a line-continuation shape; the parser
        # would consume the next char which is EOL. Ambiguous. Fail
        # closed is the right defensive move.
        # (Current parser handles this by outputting the backslash
        # verbatim and stopping; it does not produce a chain-shape by
        # itself. The regression check ensures this specific case does
        # not accidentally allow.)
        cmd = 'divineos correction "text" \\'
        # This IS safe as-is (no chain metachar outside quotes), so it
        # currently passes. Documenting for regression tracking.
        assert _has_unquoted_chain_shape(cmd) is False


class TestFeynmanRegressionSanity:
    """Regression check: previously-passing simple cases must still
    pass with the new helper. If the rewrite broke basic invocations,
    this fires."""

    def test_simple_remedy_no_quotes(self) -> None:
        assert (
            _is_safe_remedy_invocation("divineos correction hello", ("divineos correction",))
            is True
        )

    def test_simple_remedy_with_double_quoted_arg(self) -> None:
        assert (
            _is_safe_remedy_invocation('divineos correction "hello"', ("divineos correction",))
            is True
        )

    def test_simple_remedy_with_single_quoted_arg(self) -> None:
        assert (
            _is_safe_remedy_invocation("divineos correction 'hello'", ("divineos correction",))
            is True
        )

    def test_compass_ops_observe_full_form(self) -> None:
        cmd = 'divineos compass-ops observe integrity -p 0.15 -e "evidence text"'
        assert (
            _is_safe_remedy_invocation(
                cmd,
                ("divineos compass-ops observe", "divineos compass-ops dismiss"),
            )
            is True
        )

    def test_learn_with_flags(self) -> None:
        cmd = 'divineos learn "text" --confidence 0.9 --tags a,b,c'
        assert _is_safe_remedy_invocation(cmd, ("divineos learn",)) is True

    def test_learn_piped_to_tail(self) -> None:
        cmd = 'divineos learn "text" | tail -3'
        assert _is_safe_remedy_invocation(cmd, ("divineos learn",)) is True

    def test_learn_with_stderr_redirect_no_chain(self) -> None:
        # 2>&1 has an ampersand but not && — must not trip chain-shape.
        cmd = 'divineos learn "text" 2>&1'
        assert _is_safe_remedy_invocation(cmd, ("divineos learn",)) is True
