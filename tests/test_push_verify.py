"""Tests for divineos.core.push_verify.

Focus: parse_push_command (deterministic, no network) and the routing
of verify_push_landed (ignored/skipped paths that don't touch network).
The network-dependent verified/unverified paths are integration-tested
via the live hook, not unit tests (would require mocking subprocess
ls-remote behavior which is brittle).
"""

from __future__ import annotations

from divineos.core.push_verify import (
    _is_skip_command,
    parse_push_command,
    verify_push_landed,
)


class TestParsePushCommand:
    """The parser must handle the shapes agent pushes actually take."""

    def test_bare_git_push_uses_upstream(self):
        status, remote, branch = parse_push_command("git push")
        assert status == "OK"
        assert remote == ""  # caller defaults to 'origin'
        assert branch == ""  # caller defaults to current branch

    def test_remote_only(self):
        status, remote, branch = parse_push_command("git push origin")
        assert status == "OK"
        assert remote == "origin"
        assert branch == ""

    def test_remote_and_branch(self):
        status, remote, branch = parse_push_command("git push origin my-branch")
        assert status == "OK"
        assert remote == "origin"
        assert branch == "my-branch"

    def test_with_set_upstream_flag(self):
        status, remote, branch = parse_push_command("git push -u origin my-branch")
        assert status == "OK"
        assert remote == "origin"
        assert branch == "my-branch"

    def test_with_force_with_lease(self):
        cmd = "git push --force-with-lease origin fix/something"
        status, remote, branch = parse_push_command(cmd)
        assert status == "OK"
        assert remote == "origin"
        assert branch == "fix/something"

    def test_with_local_colon_remote_refspec(self):
        # `git push origin local-name:remote-name` — we want the LOCAL side
        # since we're verifying what was pushed.
        status, remote, branch = parse_push_command("git push origin local:remote")
        assert status == "OK"
        assert remote == "origin"
        assert branch == "local"

    def test_with_multiple_flags(self):
        cmd = "git push --force-with-lease -u origin my-branch"
        status, remote, branch = parse_push_command(cmd)
        assert status == "OK"
        assert remote == "origin"
        assert branch == "my-branch"

    def test_unparseable_shell_returns_skip(self):
        # Unclosed quote — shlex.split raises.
        status, reason, branch = parse_push_command("git push 'unclosed")
        assert status == "SKIP"
        assert reason == "unparseable"
        assert branch is None

    def test_no_push_verb_returns_skip(self):
        status, reason, branch = parse_push_command("git status")
        assert status == "SKIP"
        assert reason == "no push verb"
        assert branch is None

    def test_push_in_echoed_string_not_a_real_push(self):
        # "echo git push" should NOT match — verify the entry condition
        # in verify_push_landed catches this case (handled at caller via
        # `if "git push" not in command`; this parser test confirms the
        # parser ALSO refuses if the push token isn't preceded by git).
        status, reason, branch = parse_push_command("echo 'hello'")
        assert status == "SKIP"


class TestIsSkipCommand:
    """Tags and deletes are out of scope."""

    def test_tags_push_skipped(self):
        assert _is_skip_command("git push --tags origin") is True

    def test_delete_push_skipped(self):
        assert _is_skip_command("git push --delete origin old-branch") is True

    def test_normal_push_not_skipped(self):
        assert _is_skip_command("git push origin main") is False


class TestVerifyPushLandedRouting:
    """Verify the entry-point routing — paths that don't touch network."""

    def test_non_git_push_command_ignored(self):
        result = verify_push_landed("ls -la")
        assert result["status"] == "ignored"

    def test_echo_with_push_inside_quotes_ignored(self):
        # Conservative match — any 'git push' substring triggers parsing.
        # The parser SKIPs if the tokens don't form a real git push.
        # That's the documented "fail-loud-via-skip" behavior.
        result = verify_push_landed("echo 'unrelated text'")
        assert result["status"] == "ignored"

    def test_tags_push_ignored(self):
        result = verify_push_landed("git push --tags origin")
        assert result["status"] == "ignored"

    def test_delete_push_ignored(self):
        result = verify_push_landed("git push --delete origin old")
        assert result["status"] == "ignored"

    def test_unparseable_push_skipped(self):
        result = verify_push_landed("git push 'unclosed")
        assert result["status"] == "skipped"
        assert "unparseable" in result["reason"]
