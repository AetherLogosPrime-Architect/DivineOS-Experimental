"""Tests for divineos.core.command_match — does a command INVOKE or MENTION?

Every trigger phrase in this file is assembled from fragments, deliberately.
The gates these helpers serve inspect the Bash command text, so a test file
that spelled the phrases out could not be grepped, read, or edited through a
Bash tool without the gates firing on the test itself. That is not
hypothetical: on 2026-08-22 the create gate blocked a statistics script, the
grep that tried to diagnose it, and the patch that fixed it, in that order.
"""

from __future__ import annotations

import pytest

from divineos.core.command_match import (
    at_command_position,
    invokes,
    strip_quoted,
)

GH = "g" + "h"
PR = "p" + "r"
CREATE = f"{GH} {PR} " + "cre" + "ate"
MERGE = f"{GH} {PR} " + "me" + "rge"
READY = f"{GH} {PR} " + "re" + "ady"

CREATE_PAT = r"gh\s+pr\s+create(?![-\w])"
MERGE_PAT = r"gh\s+pr\s+merge\s+\d+"
READY_PAT = r"gh\s+pr\s+ready\b"


class TestStripQuoted:
    def test_double_quoted_span_is_blanked(self):
        assert strip_quoted('echo "secret"') == "echo `      `".replace("`", '"')

    def test_length_is_preserved(self):
        cmd = "echo 'abc' && ls"
        assert len(strip_quoted(cmd)) == len(cmd)

    def test_unquoted_text_is_untouched(self):
        assert strip_quoted("ls -la /tmp") == "ls -la /tmp"

    def test_escaped_quote_does_not_close_the_span(self):
        cmd = 'echo "a \\" b" tail'
        out = strip_quoted(cmd)
        assert out.endswith("tail")
        assert "a" not in out[:-4]

    def test_unterminated_quote_blanks_to_end(self):
        """An unclosed quote blanks everything after it.

        The opening delimiter itself survives — it is punctuation, not
        content — so the result is `echo "` plus spaces, not `echo`.
        Asserting the trimmed form as `echo` was this test's own first
        error, and the contract is worth stating exactly rather than
        approximately.
        """
        out = strip_quoted('echo "never closed')
        assert out.startswith('echo "')
        assert "never" not in out
        assert "closed" not in out


class TestAtCommandPosition:
    @pytest.mark.parametrize("prefix", ["", "cd x && ", "echo hi; ", "a | ", "b || "])
    def test_after_a_separator_is_a_command_position(self, prefix):
        assert at_command_position(prefix + "ls", len(prefix)) is True

    def test_behind_env_assignments_is_a_command_position(self):
        prefix = "FOO=1 BAR=2 "
        assert at_command_position(prefix + "ls", len(prefix)) is True

    def test_mid_argument_is_not_a_command_position(self):
        prefix = "grep -n "
        assert at_command_position(prefix + "ls", len(prefix)) is False


class TestInvokesAcceptsRealInvocations:
    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_bare(self, verb, pattern):
        assert invokes(f"{verb} --flag", pattern) is True

    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_chained_and_env_prefixed(self, verb, pattern):
        assert invokes(f"cd repo && {verb}", pattern) is True
        assert invokes(f"GH_TOKEN=x {verb}", pattern) is True
        assert invokes(f"echo hi; {verb}", pattern) is True


class TestInvokesRejectsMentions:
    """Each of these blocked a real command before the fix."""

    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_grepping_for_the_phrase(self, verb, pattern):
        assert invokes(f'grep -n "{verb}" audit.log', pattern) is False

    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_phrase_in_prose(self, verb, pattern):
        assert invokes(f'echo "do not run {verb} yet"', pattern) is False

    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_phrase_in_a_data_literal(self, verb, pattern):
        assert invokes(f'python -c \'d = {{"k": "{verb}"}}\'', pattern) is False

    @pytest.mark.parametrize(
        "verb,pattern",
        [(CREATE, CREATE_PAT), (MERGE + " 439", MERGE_PAT), (READY, READY_PAT)],
    )
    def test_argument_to_another_command(self, verb, pattern):
        assert invokes(f"cat notes.md | grep {verb}", pattern) is False

    def test_the_audit_submit_round_case(self):
        """The originally-reported instance, preserved as a regression.

        gh-pr-ready-gate blocked an `audit submit-round` whose focus text
        described the transition the gate guards.
        """
        cmd = f"divineos audit submit-round 'covers the {READY} transition'"
        assert invokes(cmd, READY_PAT) is False

    def test_empty_and_blank_are_not_invocations(self):
        assert invokes("", CREATE_PAT) is False
        assert invokes("   ", CREATE_PAT) is False


EXECUTE_SHAPES = [
    ("( {v} )", "subshell"),
    ("$( {v} )", "command substitution"),
    ("{{ {v}; }}", "brace group"),
    ("if true; then {v}; fi", "if/then"),
    ("for i in 1; do {v}; done", "for/do"),
    ("{v} &", "backgrounded"),
    ("true &&\n  {v}", "newline continuation"),
    ("eval {v}", "eval"),
    ("bash -c '{v}'", "bash -c, single quotes"),
    ('sh -c "{v}"', "sh -c, double quotes"),
    ("xargs {v} <<< x", "xargs"),
    ("sudo {v}", "sudo"),
    ("timeout 5 {v}", "timeout with a numeric operand"),
    ("xargs -n1 {v}", "xargs with a flag"),
    ("sudo -u me {v}", "sudo with a flag and its value"),
    ("env FOO=1 {v}", "env with an assignment"),
    ("{v} --title x", "bare"),
    ("cd repo && {v}", "after &&"),
    ("X=1 {v}", "env-prefixed"),
]

MENTION_SHAPES = [
    ('grep -n "{v}" log', "grepping for the phrase"),
    ('echo "do not {v} yet"', "prose"),
    ('python -c \'d = {{"k": "{v}"}}\'', "data literal"),
    ("cat notes.md | grep {v}", "argument to grep"),
    ("divineos audit submit-round 'about {v}'", "quoted focus text"),
    ("grep -n -A3 {v} file.sh", "grep with flags"),
    ("rg --json {v} .", "ripgrep with flags"),
    ("awk '/{v}/' f", "awk pattern"),
    ("git log --grep={v}", "git log --grep"),
    ("sed -n '/{v}/p' f", "sed pattern"),
]


class TestFalsifierProbes:
    """The falsifier of prereg-b8b95ee94720, run as tests rather than filed.

    The first version of this module was position-anchored only. Probing the
    falsifier instead of trusting the design found FIVE false negatives --
    if/then, for/do, eval, `bash -c`, and xargs all execute the verb and none
    were caught. The bare regex this replaced had zero false negatives and
    only false positives, so anchoring without these cases traded a noisy
    gate for a leaky one, which is the worse direction.

    A false negative here is the serious failure: the gate silently allows
    the thing it exists to stop.
    """

    @pytest.mark.parametrize("template,label", EXECUTE_SHAPES)
    def test_shapes_that_execute_are_caught(self, template, label):
        cmd = template.format(v=CREATE)
        assert invokes(cmd, CREATE_PAT) is True, f"false negative: {label}"

    @pytest.mark.parametrize("template,label", MENTION_SHAPES)
    def test_shapes_that_only_mention_are_not_caught(self, template, label):
        cmd = template.format(v=CREATE)
        assert invokes(cmd, CREATE_PAT) is False, f"false positive: {label}"


class TestKnownGap:
    """The heredoc hole, asserted rather than left to be rediscovered.

    A here-document body is neither quoted nor position-protected, so a line
    beginning with the verb still matches. Narrowing it needs real shell
    parsing. This test pins the CURRENT behaviour so that if someone closes
    the gap, the failure tells them the docstring needs updating too.
    """

    def test_heredoc_body_still_matches(self):
        cmd = f"cat <<EOF\n{CREATE} --title x\nEOF"
        assert invokes(cmd, CREATE_PAT) is True
