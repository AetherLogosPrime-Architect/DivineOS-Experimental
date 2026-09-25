"""The --no-verify gate, and the position it was anchored to.

WHY THIS FILE EXISTS. Until 2026-08-22 this gate had no tests at all, and it
carried a bug that made it inert for the way I actually type commands.

``decide()`` used ``tokens.index("git")`` -- the FIRST git in the whole command
-- read the token after it as the subcommand, and returned allow when that was
not commit/push. So::

    git commit --no-verify -m x                 -> DENIED
    git add -A && git commit --no-verify -m x   -> ALLOWED

The second is the ordinary shape of a commit. Every command in this harness is
prefixed ``cd "C:/..." && ...``, so in practice the gate was anchored to a
position I am almost never in.

It was not hanging, not unregistered, not misconfigured. Andrew asked me to
"fix the reaching using automation" after I reached for --no-verify twice in
one session; the reaching went unchallenged because the guard could not see it.
The gate's own telemetry showed ONE lifetime use of its reason variable, which
reads as excellent discipline and actually meant almost nothing reached it.

The over-fire cases below matter as much as the under-fire ones: a gate that
blocks ``grep -n`` or ``git log -n 5`` trains me to reach for the escape hatch,
which is the failure this gate exists to prevent, arriving by the other door.
"""

from __future__ import annotations

import pytest

from divineos.core.no_verify_cost import decide


def _cmd(command: str) -> dict[str, str]:
    return {"command": command}


def _denied(command: str) -> bool:
    return decide(_cmd(command)) is not None


class TestTheFirstGitIsNotTheOnlyGit:
    """The bug, pinned. Each of these has a git commit behind another command."""

    @pytest.mark.parametrize(
        "command",
        [
            "git add -A && git commit --no-verify -m x",
            'cd "C:/DIVINE OS/DivineOS-Experimental" && git commit -q --no-verify -m x',
            'cd "/tmp/wt" && git add -A src && git commit -q --no-verify -F -',
            "git status && git push --no-verify",
            "git fetch origin && git rebase main && git push --no-verify",
        ],
    )
    def test_git_commit_behind_another_command_is_still_caught(self, command: str) -> None:
        assert _denied(command), f"gate went silent on: {command}"

    def test_the_bare_form_still_denies(self) -> None:
        """The one case the old code DID catch. Regression guard both ways."""
        assert _denied("git commit --no-verify -m x")


class TestShortFormCounts:
    """``-n`` is git commit's short spelling of --no-verify."""

    def test_dash_n_on_commit_is_caught(self) -> None:
        assert _denied('cd "C:/x" && git commit -n -m x')

    def test_dash_n_on_push_is_NOT_no_verify(self) -> None:
        """`-n` is --dry-run for push, --no-verify only for commit.

        I wrote this assertion as `... or True` first, which always passes and
        tests nothing -- and writing it is what surfaced that my flag list
        applied `-n` to both subcommands. A rehearsal push would have been
        denied. Same class as the gate this file is about: the fake assertion
        and the over-firing gate both look like coverage and provide none.
        """
        assert not _denied("git push -n origin main")


class TestOverFiringIsItsOwnFailure:
    """A gate that cries wolf teaches the reach it exists to prevent.

    These are the cases where ``-n`` or the literal string appears but no
    unverified git write does. Blocking any of them would be the reason a
    future me starts looking for the escape hatch by habit.
    """

    @pytest.mark.parametrize(
        "command",
        [
            "git add -A && git commit -m x",
            "grep -n pattern file.txt && git commit -m x",
            "git log -n 5",
            'echo "never use --no-verify" && git status',
            "sort -n numbers.txt",
            "git diff --stat && git add -A",
        ],
    )
    def test_allowed(self, command: str) -> None:
        assert not _denied(command), f"gate over-fired on: {command}"


class TestTheNamedReasonStillOpensIt:
    """Blocking is not the goal; naming the reason is. The escape must work.

    A gate whose escape hatch is broken is the painted-door shape -- and this
    substrate has shipped that at least three times, so it gets a test here.
    """

    def test_a_named_reason_allows_the_bypass(self) -> None:
        cmd = (
            'DIVINEOS_NO_VERIFY_REASON="precommit cannot run in a bare worktree" '
            "git commit --no-verify -m x"
        )
        assert decide(_cmd(cmd)) is None

    def test_a_stub_reason_does_not(self) -> None:
        cmd = 'DIVINEOS_NO_VERIFY_REASON="x" git commit --no-verify -m x'
        assert decide(_cmd(cmd)) is not None


class TestFailSoft:
    def test_empty_input_is_allowed(self) -> None:
        assert decide(None) is None
        assert decide({}) is None
        assert decide(_cmd("")) is None

    def test_malformed_quoting_does_not_raise(self) -> None:
        """Another gate catches broken shell; this one must not explode."""
        assert decide(_cmd("git commit --no-verify -m 'unterminated")) is None


class TestMentionIsNotUse:
    """The gate blocked its own fix, and the block was self-selecting.

    ``shlex.split`` flattens a heredoc, so the BODY of
    ``git commit -F - <<EOF ... EOF`` arrives as bare tokens and the gate reads
    the COMMIT MESSAGE as a second command. On 2026-08-22 the message
    explaining this very gate quoted ``git commit --no-verify -m x`` as an
    example of the bug, and the gate denied the commit that fixed it.

    Worst possible selectivity: the commit messages most likely to quote
    --no-verify are the ones documenting a --no-verify defect, so the gate
    fires hardest on the work that repairs it. Same class as
    ``_strip_quoted_spans`` in the lepos translation gate -- a checker that
    cannot tell talking-about from doing.
    """

    def test_a_commit_message_quoting_the_flag_is_not_a_use(self) -> None:
        cmd = "git commit -q -F - <<'EOF'\n  git commit --no-verify -m x  -> DENY\nEOF"
        assert not _denied(cmd)

    def test_a_real_no_verify_opening_a_heredoc_is_still_caught(self) -> None:
        """Only the BODY is data. The line that opens it is still a command."""
        cmd = "git commit -q --no-verify -F - <<'EOF'\nmessage\nEOF"
        assert _denied(cmd)

    def test_unquoted_heredoc_delimiter_also_strips(self) -> None:
        cmd = "git commit -F - <<EOF\ngit commit --no-verify\nEOF"
        assert not _denied(cmd)
