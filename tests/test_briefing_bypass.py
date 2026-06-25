"""Tests for divineos.core.briefing_bypass — the bootstrap-command allowlist."""

from __future__ import annotations

from divineos.core.briefing_bypass import (
    BYPASS_PREFIXES,
    command_segments,
    is_bypass_bash_command,
)


class TestCommandSegments:
    """Shell-chain split for bypass-check on each segment."""

    def test_single_command_returns_one_segment(self):
        assert command_segments("divineos briefing") == ["divineos briefing"]

    def test_and_chain_splits(self):
        assert command_segments("cd /tmp && divineos briefing") == [
            "cd /tmp",
            "divineos briefing",
        ]

    def test_semicolon_chain_splits(self):
        assert command_segments("ls; divineos hud") == ["ls", "divineos hud"]

    def test_pipe_chain_splits(self):
        assert command_segments("echo x | divineos ask") == ["echo x", "divineos ask"]

    def test_newline_chain_splits(self):
        assert command_segments("ls\ndivineos briefing") == ["ls", "divineos briefing"]

    def test_empty_segments_dropped(self):
        assert command_segments("&& divineos briefing &&") == ["divineos briefing"]

    def test_complex_chain(self):
        assert command_segments("cd /repo && git status; divineos briefing | tee out.txt") == [
            "cd /repo",
            "git status",
            "divineos briefing",
            "tee out.txt",
        ]


class TestIsBypassBashCommand:
    """The bootstrap-command allowlist check."""

    def test_bare_briefing_allowed(self):
        assert is_bypass_bash_command("divineos briefing") is True

    def test_briefing_id_allowed(self):
        assert is_bypass_bash_command("divineos briefing-id abc123") is True

    def test_init_preflight_recall_ask_hud_context_goal(self):
        for cmd in (
            "divineos init",
            "divineos preflight",
            "divineos recall",
            "divineos ask 'topic'",
            "divineos hud",
            "divineos context",
            "divineos goal add 'x'",
        ):
            assert is_bypass_bash_command(cmd) is True, f"expected bypass: {cmd}"

    def test_cd_and_briefing_allowed(self):
        # The common case: cwd reset between bash calls means most divineos
        # invocations arrive as `cd <repo> && divineos briefing`. Bypass must
        # match the second segment.
        assert (
            is_bypass_bash_command("cd /c/DIVINE\\ OS/DivineOS-Experimental && divineos briefing")
            is True
        )

    def test_echo_of_briefing_text_not_bypass(self):
        # `echo "divineos briefing"` — segment starts with `echo`, not with
        # `divineos`, so this is correctly NOT a bypass. The fix-instruction
        # text in deny-messages can mention the command without triggering
        # a bypass.
        assert is_bypass_bash_command('echo "divineos briefing"') is False

    def test_unrelated_command_not_bypass(self):
        assert is_bypass_bash_command("ls -la") is False
        assert is_bypass_bash_command("git status") is False
        assert is_bypass_bash_command("python -c 'print(1)'") is False

    def test_divineos_non_bypass_subcommand_blocked(self):
        # divineos sleep / divineos learn / divineos commit are NOT in the
        # bypass set — they should be denied when briefing is stale.
        assert is_bypass_bash_command("divineos sleep") is False
        assert is_bypass_bash_command("divineos learn 'something'") is False
        assert is_bypass_bash_command("divineos commit") is False

    def test_empty_command(self):
        assert is_bypass_bash_command("") is False

    def test_only_whitespace(self):
        assert is_bypass_bash_command("   ") is False


class TestBypassPrefixesContract:
    """Lock the public BYPASS_PREFIXES tuple so any change is intentional.

    Each prefix in this list corresponds to a known-safe bootstrap command
    that must work even when briefing is stale. Adding to the list is a
    real decision — these tests force the decision to be visible.
    """

    def test_briefing_in_list(self):
        assert "divineos briefing" in BYPASS_PREFIXES

    def test_briefing_id_in_list(self):
        # Without this, the recall-challenge cure ('divineos briefing-id <id>')
        # is itself blocked — catch-22.
        assert "divineos briefing-id" in BYPASS_PREFIXES

    def test_init_in_list(self):
        assert "divineos init" in BYPASS_PREFIXES

    def test_preflight_in_list(self):
        assert "divineos preflight" in BYPASS_PREFIXES

    def test_recall_in_list(self):
        assert "divineos recall" in BYPASS_PREFIXES

    def test_ask_in_list(self):
        assert "divineos ask" in BYPASS_PREFIXES

    def test_hud_in_list(self):
        assert "divineos hud" in BYPASS_PREFIXES

    def test_context_in_list(self):
        assert "divineos context" in BYPASS_PREFIXES

    def test_goal_in_list(self):
        assert "divineos goal" in BYPASS_PREFIXES

    def test_exact_count(self):
        # Locking the count means any addition forces a separate test
        # update — the addition cannot be silent.
        assert len(BYPASS_PREFIXES) == 9
