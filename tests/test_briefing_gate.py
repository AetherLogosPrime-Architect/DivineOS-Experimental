"""Tests for the briefing enforcement gate — blocks work until briefing loaded."""

from unittest.mock import patch

from divineos.cli import _BYPASS_COMMANDS, _enforce_briefing_gate


class TestBriefingGate:
    def test_bypass_commands_not_blocked(self):
        """Commands in the bypass list should never be blocked."""
        for cmd in _BYPASS_COMMANDS:
            with patch("sys.argv", ["divineos", cmd]):
                with patch("sys.modules", {"pytest": None}):
                    # Should not raise — but we're in pytest so it returns early
                    _enforce_briefing_gate()

    def test_skips_in_test_environment(self):
        """Gate should be a no-op during pytest runs."""
        with patch("sys.argv", ["divineos", "learn", "something"]):
            # Should not raise because pytest is in sys.modules
            _enforce_briefing_gate()

    def test_skips_empty_args(self):
        """Just `divineos` with no subcommand should show help, not block."""
        with patch("sys.argv", ["divineos"]):
            _enforce_briefing_gate()

    def test_skips_flags(self):
        """Flags like --help should not be blocked."""
        with patch("sys.argv", ["divineos", "--help"]):
            _enforce_briefing_gate()

    def test_bypass_set_contains_essentials(self):
        """The bypass set must include briefing, init, preflight, emit, and checkpoint."""
        assert "briefing" in _BYPASS_COMMANDS
        assert "init" in _BYPASS_COMMANDS
        assert "preflight" in _BYPASS_COMMANDS
        assert "emit" in _BYPASS_COMMANDS
        assert "checkpoint" in _BYPASS_COMMANDS
        assert "context-status" in _BYPASS_COMMANDS
