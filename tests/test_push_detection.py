"""Tests for is_git_push_command — matcher for the check-branch-on-push hook.

Per Aether 2026-06-06 lesson: test the Python matcher directly via pytest.
Bash-hook integration testing is risky because invoking bash to test the
live hook triggers the live hook recursively (the cascade-deadlock pattern
from the obligation gate's broken-day-one bug).

Regression cases encode the substring-in-data class so future false-fires
are caught by the test rather than by Andrew at runtime.
"""

from __future__ import annotations

from divineos.core.push_detection import is_git_push_command


class TestGitPushMatcher:
    # ── Real git push commands must match ────────────────────────────

    def test_plain_git_push_matches(self) -> None:
        assert is_git_push_command("git push")

    def test_git_push_with_remote_matches(self) -> None:
        assert is_git_push_command("git push origin")

    def test_git_push_with_remote_and_branch_matches(self) -> None:
        assert is_git_push_command("git push origin main")

    def test_git_push_with_set_upstream_matches(self) -> None:
        assert is_git_push_command("git push -u origin feature/x")

    def test_git_push_force_matches(self) -> None:
        # Force pushes are pushes; the check-branch gate is exactly
        # where to surface "are you sure?" before they land.
        assert is_git_push_command("git push --force-with-lease origin main")

    def test_cd_then_git_push_matches(self) -> None:
        # Common chained shape: change directory, then push.
        assert is_git_push_command("cd /tmp/repo && git push")

    def test_git_push_with_leading_whitespace_matches(self) -> None:
        assert is_git_push_command("   git push origin main")

    # ── Other git subcommands must NOT match ─────────────────────────

    def test_git_status_does_not_match(self) -> None:
        assert not is_git_push_command("git status")

    def test_git_pull_does_not_match(self) -> None:
        assert not is_git_push_command("git pull origin main")

    def test_git_fetch_does_not_match(self) -> None:
        assert not is_git_push_command("git fetch origin")

    def test_git_log_does_not_match(self) -> None:
        assert not is_git_push_command("git log --oneline -5")

    def test_pushd_does_not_match(self) -> None:
        # `pushd` contains "push" as substring but isn't `git push`.
        assert not is_git_push_command("pushd /tmp && git status")

    # ── Substring-in-data must NOT trigger (cascade-deadlock class) ──

    def test_echo_containing_command_does_not_match(self) -> None:
        # The cascade-failure shape: command string literally contains
        # the phrase "git push" inside echo arguments.
        assert not is_git_push_command("echo 'git push'")

    def test_quoted_string_in_other_command_does_not_match(self) -> None:
        assert not is_git_push_command("grep 'git push' .claude/hooks/check-branch-on-push.sh")

    def test_heredoc_containing_git_push_does_not_match(self) -> None:
        assert not is_git_push_command("cat << EOF\ngit push origin main\nEOF")

    def test_command_argument_containing_git_push_does_not_match(self) -> None:
        # A different tool whose argument happens to contain "git push".
        assert not is_git_push_command("python -c \"print('git push')\"")

    # ── Edge cases ───────────────────────────────────────────────────

    def test_empty_command_does_not_match(self) -> None:
        assert not is_git_push_command("")

    def test_whitespace_only_does_not_match(self) -> None:
        assert not is_git_push_command("   \n  ")

    def test_compound_with_real_push_in_second_segment_matches(self) -> None:
        # Real shape: precommit-check before push.
        assert is_git_push_command("bash scripts/precommit.sh && git push origin main")
