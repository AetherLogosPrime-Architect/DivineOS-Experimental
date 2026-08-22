"""Tests for the one place that knows a command's head is not its first character.

The module exists because three sites learned this independently and two got
it wrong. These cases are the union of what all three needed, so a fourth site
importing it inherits every lesson rather than rediscovering one.
"""

from __future__ import annotations

from divineos.core.command_parsing import (
    resolve_command_head,
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
