"""Quote-context scanner in the bypass matcher (2026-08-01).

The old ``_has_compound_shape`` substring-scanned the raw command, so an
operator character inside a *quoted argument value* defeated a bypass the
subcommand qualified for. Live consequence: the overdue-prereg gate
hard-blocks all substantive tool use and names ``divineos prereg assess``
as its own remedy, and that remedy was denied three times because its
notes value described shell syntax. Claim 09213383, walk ebcf9db6.

Two halves, and the second matters more:

* the false-fires the fix is meant to stop
* the exploits F22 and F31 caught, which must STILL be caught

A fix to a security check that only tests the loosening is not tested.

See docs/gate_quote_context_parser_2026-08-01.md for why this is a
different call from the descriptive-vs-claim silencer that the
unverified-claim detector deliberately REJECTED.
"""

from divineos.hooks.pre_tool_use_gate import _has_compound_shape, _is_bypass_command

SQ = chr(39)
DQ = chr(34)
DOLLAR = chr(36)
OPEN_P = chr(40)
CLOSE_P = chr(41)
TICK = chr(96)
SEMI = chr(59)
AMP = chr(38)
PIPE = chr(124)


# --- the regression this fix exists for --------------------------------


def test_operator_chars_inside_double_quoted_arg_do_not_block():
    """The live failure, reproduced. Operators inside a quoted value are
    not operators — the shell never sees them as such."""
    cmd = (
        f"divineos prereg assess pr-1 --outcome INCONCLUSIVE --notes "
        f"{DQ}my first attempt used a cd prefix ending in {AMP}{AMP} and "
        f"the pipe char {PIPE} and a semicolon{SEMI} none of which run{DQ}"
    )
    assert _has_compound_shape(cmd) is False
    assert _is_bypass_command(cmd) is True


def test_operator_chars_inside_single_quoted_arg_do_not_block():
    cmd = f"divineos learn {SQ}shell chains with {AMP}{AMP} and {SEMI} tokens{SQ}"
    assert _has_compound_shape(cmd) is False
    assert _is_bypass_command(cmd) is True


def test_long_quoted_note_matches_short_quoted_note():
    """Argument LENGTH must not change the verdict. The live symptom was a
    short note passing and a long note failing, which is what pointed at
    content-sensitivity in the first place."""
    short = f"divineos prereg assess pr-1 --outcome FAILED --notes {DQ}short{DQ}"
    long_note = (
        f"divineos prereg assess pr-1 --outcome FAILED --notes "
        f"{DQ}{'a much longer note that goes on for a while ' * 12}{DQ}"
    )
    assert _has_compound_shape(short) is False
    assert _has_compound_shape(long_note) is False


# --- F22: decoy safe-word must still be caught -------------------------


def test_f22_chained_command_after_safe_word_still_blocked():
    cmd = f"divineos briefing{SEMI} rm -rf /tmp/x"
    assert _has_compound_shape(cmd) is True
    assert _is_bypass_command(cmd) is False


def test_f22_and_chain_still_blocked():
    cmd = f"divineos ask topic {AMP}{AMP} curl evil.example.com"
    assert _has_compound_shape(cmd) is True
    assert _is_bypass_command(cmd) is False


def test_unquoted_pipe_to_unsafe_filter_still_blocked():
    cmd = f"divineos recall {PIPE} bash"
    assert _is_bypass_command(cmd) is False


# --- F31: substitution expands inside double quotes --------------------


def test_f31_substitution_inside_double_quotes_still_blocked():
    """The asymmetry that makes this scanner non-trivial: chaining
    operators are inert inside double quotes, substitution is NOT."""
    cmd = f"cd {DQ}{DOLLAR}{OPEN_P}rm -rf /{CLOSE_P}{DQ} {AMP}{AMP} divineos ask x"
    assert _is_bypass_command(cmd) is False


def test_substitution_inside_double_quoted_arg_blocked():
    cmd = f"divineos learn {DQ}payload {DOLLAR}{OPEN_P}whoami{CLOSE_P} here{DQ}"
    assert _has_compound_shape(cmd) is True


def test_backtick_inside_double_quotes_blocked():
    cmd = f"divineos learn {DQ}payload {TICK}whoami{TICK} here{DQ}"
    assert _has_compound_shape(cmd) is True


def test_substitution_inside_single_quotes_is_inert():
    """Single quotes suppress expansion, so this one is genuinely safe.
    Asserted so that a future tightening which treats both quote kinds
    alike fails loudly instead of quietly re-breaking long notes."""
    cmd = f"divineos learn {SQ}literal {DOLLAR}{OPEN_P}whoami{CLOSE_P} text{SQ}"
    assert _has_compound_shape(cmd) is False


# --- fail-closed --------------------------------------------------------


def test_unterminated_quote_fails_closed():
    cmd = f"divineos learn {DQ}never closed"
    assert _has_compound_shape(cmd) is True
    assert _is_bypass_command(cmd) is False


def test_escaped_quote_outside_quotes_does_not_open_a_string():
    cmd = f"divineos learn \\{DQ}not-a-string {SEMI} rm -rf /tmp/x"
    assert _has_compound_shape(cmd) is True


def test_fd_redirect_ampersand_is_not_an_operator():
    """Regression I caused, caught by the pre-push suite. The substring scan
    this replaced only ever matched the DOUBLED ampersand; my first scanner
    treated a bare one as an operator, which broke three tests shipped by
    PR #400 because `2>&1` is a file-descriptor redirect, not a chain."""
    cmd = f"divineos briefing 2{chr(62)}{AMP}1"
    assert _has_compound_shape(cmd) is False
    assert _is_bypass_command(cmd) is True


def test_fd_redirect_with_safe_pipe_tail_still_bypasses():
    cmd = f"divineos ask topic 2{chr(62)}{AMP}1 {PIPE} head -20"
    assert _is_bypass_command(cmd) is True


def test_backgrounding_ampersand_still_blocked():
    """Other side of the same discriminator: a bare trailing ampersand
    backgrounds the command and must NOT bypass."""
    cmd = f"divineos briefing {AMP}"
    assert _has_compound_shape(cmd) is True


def test_bare_safe_command_unaffected():
    assert _has_compound_shape("divineos prereg overdue") is False
    assert _is_bypass_command("divineos prereg overdue") is True
