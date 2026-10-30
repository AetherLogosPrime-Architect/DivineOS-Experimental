"""The merge gate refuses a body it cannot read as a literal.

2026-10-17: #603 and #679 were merged with `--body "$B"`, B holding a
tree-hash after the round. The gate read the command's text, saw a variable and
no trailer, and let both through; main's Integrity Audit went red on both.
"""

from __future__ import annotations

from divineos.core import pr_merge_gate

_TREE = "f" * 40


def _gate(command: str):
    return pr_merge_gate.block_reason(command)


def test_the_two_real_merge_shapes_that_went_red_are_refused():
    shape_603 = 'T=$(gh pr view 603 --json title --jq .title); B=$(gh pr view 603 --json body --jq .body); gh pr merge 603 --squash --subject "$T (#603)" --body "$B"'
    shape_679 = 'gh pr merge 679 --squash --subject "$T (#679)" --body "$B"'
    for command in (shape_603, shape_679):
        reason = _gate(command)
        assert reason is not None, command
        assert "ship" in reason


def test_a_command_substitution_other_than_the_printed_heredoc_is_refused():
    reason = _gate('gh pr merge 5 --squash --body "$(gh pr view 5 --json body --jq .body)"')
    assert reason is not None


def test_a_backtick_is_refused():
    assert _gate("gh pr merge 5 --squash --body `cat body.txt`") is not None


def test_a_single_quoted_dollar_is_literal_and_passes():
    command = "gh pr merge 5 --squash --body 'costs $5 and ${x} are literal'"
    assert _gate(command) is None


def test_the_literal_heredoc_the_gate_prints_still_passes():
    command = (
        "gh pr merge 5 --squash --body \"$(cat <<'EOF'\n"
        "A fix.\n\nExternal-Review: round-abc123\n"
        'EOF\n)"'
    )
    assert _gate(command) is None


def test_the_expansion_in_an_earlier_statement_is_not_this_merges():
    # The variable is assigned before the merge; the merge itself is literal.
    assert _gate("B=1; gh pr merge 5 --squash --body 'fix'") is None


def test_a_body_read_from_a_file_is_refused():
    for flag in ("--body-file msg.txt", "-F msg.txt", "--body-file=msg.txt"):
        assert _gate(f"gh pr merge 5 --squash {flag}") is not None, flag


def test_the_word_dash_f_inside_a_quoted_body_is_not_the_flag():
    assert _gate('gh pr merge 5 --squash --body "use -F for files"') is None


def test_an_escaped_dollar_in_double_quotes_is_literal():
    assert _gate('gh pr merge 5 --squash --body "costs \\$5"') is None


def test_the_special_parameters_that_expand_to_text_are_refused():
    for body in ('"$?"', '"$$"', '"$1"'):
        assert _gate(f"gh pr merge 5 --squash --body {body}") is not None, body


def test_a_redirect_before_the_body_does_not_hide_a_variable():
    """Aria's cold read: the redirect's ampersand was taken for the end of the
    statement, so the variable behind it was never seen."""
    for redirect in ("2>&1", "&>/dev/null", ">&2"):
        command = f'gh pr merge 5 --squash {redirect} --body "$B"'
        assert _gate(command) is not None, redirect
    # Control: the same body with no redirect is refused, so the probe can see it.
    assert _gate('gh pr merge 5 --squash --body "$B"') is not None


def test_an_ansi_c_string_that_decodes_a_tree_hash_is_refused():
    """Aletheia's hold on #688: $'...' decodes escapes, so a colon written as \\x3a sends a
    'tree-hash:' the gate never saw. Control: the plain single-quoted form is still literal."""
    sneaky = (
        "gh pr merge 5 --squash --body $'fix\\n\\nExternal-Review: round-abc tree-hash\\x3a"
        + "f" * 40
        + "'"
    )
    assert _gate(sneaky) is not None
    assert _gate("gh pr merge 5 --squash --body 'fix'") is None
    assert _gate('gh pr merge 5 --squash --body $"fix"') is not None


def test_a_double_ampersand_chain_still_ends_the_statement():
    assert _gate("gh pr merge 5 --squash --body 'fix' && echo \"$B\"") is None
    assert _gate("gh pr merge 5 --squash --body 'fix' 2>&1 && echo \"$B\"") is None


def test_a_chained_command_after_the_merge_is_not_judged():
    assert _gate("gh pr merge 5 --squash --body 'fix' && echo $HOME") is None


def test_a_plain_literal_merge_passes():
    assert _gate('gh pr merge 5 --squash --body "fix"') is None


def test_a_tree_hash_typed_in_the_body_is_still_refused_first():
    command = f'gh pr merge 5 --squash --body "fix\n\nExternal-Review: round-abc tree-hash:{_TREE}"'
    reason = _gate(command)
    assert reason is not None
    assert "tree-hash" in reason


def test_a_command_that_is_not_a_merge_is_never_judged():
    assert _gate('echo "$B" && gh pr view 5') is None
