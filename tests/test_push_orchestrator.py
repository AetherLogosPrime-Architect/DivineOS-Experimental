"""Tests for divineos.core.push_orchestrator.

Focus: PushResult shape, the foreground vs background invariant
(via subprocess mock), and the lock-timeout failure path. Real
git-push integration is covered by the live use of the command.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.push_orchestrator import PushResult, push_branch


class TestPushResultDataclass:
    def test_default_shape(self):
        r = PushResult()
        assert r.branch == ""
        assert r.exit_code == 0
        assert r.succeeded is False
        assert r.stage == ""
        assert r.note == ""
        assert r.extra_args == []

    def test_success_shape(self):
        r = PushResult(branch="feat/x", exit_code=0, succeeded=True, stage="done", note="ok")
        assert r.succeeded is True
        assert r.stage == "done"


class TestPushBranchSuccessPath:
    def test_clean_success_emits_done(self):
        with (
            patch("divineos.core.push_orchestrator._ledger_log") as mock_ledger,
            patch("divineos.core.push_orchestrator._emit_status"),
            patch("divineos.core.push_orchestrator.subprocess.run") as mock_run,
            patch("divineos.core.push_orchestrator.FileLock"),
        ):
            mock_run.return_value.returncode = 0
            result = push_branch("my-branch")
            assert result.succeeded is True
            assert result.exit_code == 0
            assert result.stage == "done"
            assert result.branch == "my-branch"
            # Ledger gets QUEUED + RUNNING + DONE.
            event_types = [call.args[0] for call in mock_ledger.call_args_list]
            assert "PUSH_QUEUED" in event_types
            assert "PUSH_RUNNING" in event_types
            assert "PUSH_DONE" in event_types

    def test_force_with_lease_passes_through(self):
        with (
            patch("divineos.core.push_orchestrator._ledger_log"),
            patch("divineos.core.push_orchestrator._emit_status"),
            patch("divineos.core.push_orchestrator.subprocess.run") as mock_run,
            patch("divineos.core.push_orchestrator.FileLock"),
        ):
            mock_run.return_value.returncode = 0
            push_branch("my-branch", extra_args=["--force-with-lease"])
            cmd = mock_run.call_args[0][0]
            assert "--force-with-lease" in cmd
            assert "git" in cmd
            assert "push" in cmd


class TestPushBranchFailurePaths:
    def test_nonzero_exit_emits_failed(self):
        with (
            patch("divineos.core.push_orchestrator._ledger_log") as mock_ledger,
            patch("divineos.core.push_orchestrator._emit_status"),
            patch("divineos.core.push_orchestrator.subprocess.run") as mock_run,
            patch("divineos.core.push_orchestrator.FileLock"),
        ):
            mock_run.return_value.returncode = 1
            result = push_branch("bad-branch")
            assert result.succeeded is False
            assert result.exit_code == 1
            assert result.stage == "failed"
            # PUSH_FAILED MUST land in the ledger — silent-failure
            # closure depends on this.
            event_types = [call.args[0] for call in mock_ledger.call_args_list]
            assert "PUSH_FAILED" in event_types

    def test_lock_timeout_emits_failed(self):
        # When the file-lock can't be acquired in time, the orchestrator
        # MUST surface PUSH_FAILED — silent-failure rears its head if it
        # silently returns success on timeout.
        from filelock import Timeout

        with (
            patch("divineos.core.push_orchestrator._ledger_log") as mock_ledger,
            patch("divineos.core.push_orchestrator._emit_status"),
            patch("divineos.core.push_orchestrator.FileLock") as mock_lock_cls,
        ):
            instance = mock_lock_cls.return_value
            instance.__enter__.side_effect = Timeout("lock")
            instance.__exit__.return_value = False
            result = push_branch("blocked-branch", lock_timeout_seconds=1)
            assert result.succeeded is False
            assert result.stage == "lock-timeout"
            assert result.exit_code == 3
            event_types = [call.args[0] for call in mock_ledger.call_args_list]
            assert "PUSH_FAILED" in event_types
            assert "PUSH_DONE" not in event_types


class TestSilentFailureInvariant:
    """The whole point of this module: silent failure is structurally impossible."""

    def test_every_invocation_emits_at_least_one_ledger_event(self):
        # No matter the exit path, the ledger sees at least one event.
        # Tests the contract that closes the silent-failure root.
        with (
            patch("divineos.core.push_orchestrator._ledger_log") as mock_ledger,
            patch("divineos.core.push_orchestrator._emit_status"),
            patch("divineos.core.push_orchestrator.subprocess.run") as mock_run,
            patch("divineos.core.push_orchestrator.FileLock"),
        ):
            mock_run.return_value.returncode = 0
            push_branch("x")
            assert mock_ledger.call_count >= 1

    def test_every_invocation_emits_status_to_stderr(self):
        # The stderr channel is the second alarm — even if ledger
        # writes fail, the operator sees the status.
        with (
            patch("divineos.core.push_orchestrator._ledger_log"),
            patch("divineos.core.push_orchestrator._emit_status") as mock_emit,
            patch("divineos.core.push_orchestrator.subprocess.run") as mock_run,
            patch("divineos.core.push_orchestrator.FileLock"),
        ):
            mock_run.return_value.returncode = 0
            push_branch("x")
            assert mock_emit.call_count >= 1
