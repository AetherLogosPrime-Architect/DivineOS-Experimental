"""Tests for `divineos automerge` — auto-merge status surface for open PRs.

The command pairs with `gh pr merge --auto` to close the verification loop —
clicking auto-merge is NOT the same as the merge happening. The 2026-06-11
batch session burned cycles on this exact gap (I'd arm auto-merge and then
say "queued for landing" while CI still had to clear). The surface fixes
the conflation by showing which queued PRs are progressing vs stalled.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli.automerge_commands import (
    _classify,
    _first_problem_check,
)


class TestClassify:
    """Five mutually-exclusive classes typed by the union of mergeable +
    mergeStateStatus + autoMergeRequest fields from `gh pr list --json`."""

    def test_ready_clean_no_auto(self) -> None:
        """CLEAN + no auto-merge = READY (click-merge-now)."""
        pr = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "CLEAN",
            "autoMergeRequest": None,
        }
        assert _classify(pr) == "READY"

    def test_armed_blocked_with_auto(self) -> None:
        """BLOCKED + auto-merge-armed = ARMED (queued behind CI)."""
        pr = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BLOCKED",
            "autoMergeRequest": {"mergeMethod": "SQUASH"},
        }
        assert _classify(pr) == "ARMED"

    def test_blocked_no_auto(self) -> None:
        """BLOCKED + no auto-merge = BLOCKED (needs attention)."""
        pr = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BLOCKED",
            "autoMergeRequest": None,
        }
        assert _classify(pr) == "BLOCKED"

    def test_dirty_conflicting(self) -> None:
        """CONFLICTING mergeability = DIRTY (needs rebase/manual fix)."""
        pr = {
            "mergeable": "CONFLICTING",
            "mergeStateStatus": "DIRTY",
            "autoMergeRequest": None,
        }
        assert _classify(pr) == "DIRTY"

    def test_unknown_mergeability_not_yet_computed(self) -> None:
        """UNKNOWN mergeability = UNKNOWN (gh hasn't computed yet)."""
        pr = {
            "mergeable": "UNKNOWN",
            "mergeStateStatus": "UNKNOWN",
            "autoMergeRequest": None,
        }
        assert _classify(pr) == "UNKNOWN"

    def test_behind_with_auto_is_armed(self) -> None:
        """BEHIND + auto-merge counts as ARMED — the queue handles rebase."""
        pr = {
            "mergeable": "MERGEABLE",
            "mergeStateStatus": "BEHIND",
            "autoMergeRequest": {"mergeMethod": "SQUASH"},
        }
        assert _classify(pr) == "ARMED"


class TestFirstProblemCheck:
    """The BLOCKED rows show the first failing or pending check to make
    'why isn't this landing' visible without clicking into each PR."""

    def test_empty_returns_empty(self) -> None:
        assert _first_problem_check([]) == ""
        assert _first_problem_check(None) == ""

    def test_failure_named_first(self) -> None:
        checks = [
            {"name": "test (3.11)", "conclusion": "FAILURE"},
            {"name": "lint", "conclusion": "SUCCESS"},
        ]
        assert _first_problem_check(checks) == "FAIL: test (3.11)"

    def test_pending_when_no_failures(self) -> None:
        checks = [
            {"name": "test (3.11)", "conclusion": "SUCCESS"},
            {"name": "multi-party-review", "status": "PENDING"},
        ]
        assert _first_problem_check(checks) == "PENDING: multi-party-review"

    def test_failure_beats_pending_in_priority(self) -> None:
        """A failed check + a pending check → report the failure first.
        Failures need action now; pendings just need time."""
        checks = [
            {"name": "pending-thing", "status": "PENDING"},
            {"name": "failed-thing", "conclusion": "FAILURE"},
        ]
        assert _first_problem_check(checks) == "FAIL: failed-thing"

    def test_all_clean_returns_empty(self) -> None:
        """Clean check rollup → no problem label."""
        checks = [
            {"name": "test (3.11)", "conclusion": "SUCCESS"},
            {"name": "lint", "conclusion": "SUCCESS"},
        ]
        assert _first_problem_check(checks) == ""

    def test_cancelled_counts_as_failure(self) -> None:
        checks = [{"name": "ci", "conclusion": "CANCELLED"}]
        assert _first_problem_check(checks) == "FAIL: ci"

    def test_workflow_name_fallback_when_no_name(self) -> None:
        """gh returns either `name` or `workflowName`; we fall back."""
        checks = [{"workflowName": "Integrity Audit", "conclusion": "FAILURE"}]
        assert _first_problem_check(checks) == "FAIL: Integrity Audit"


class TestCommandRegistered:
    """Smoke test: the command is wired into the CLI and shows help."""

    def test_help_lists_flags(self) -> None:
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["automerge", "--help"])
        assert result.exit_code == 0
        # All three filter flags must appear
        assert "--armed" in result.output
        assert "--ready" in result.output
        assert "--blocked" in result.output


class TestEmptyResponse:
    """When gh returns no PRs (auth failure, network down, etc.), the
    command must say so honestly rather than print an empty list and
    look successful."""

    def test_empty_pr_list_says_so(self, monkeypatch) -> None:
        from divineos.cli import automerge_commands, cli

        monkeypatch.setattr(
            automerge_commands,
            "_gh_pr_list_with_states",
            lambda: [],
        )
        runner = CliRunner()
        result = runner.invoke(cli, ["automerge"])
        # Non-fatal — exits 0 with a diagnostic.
        assert result.exit_code == 0
        # Names gh and points at auth-status as the most common cause.
        assert "no PRs" in result.output.lower() or "auth status" in result.output.lower()
