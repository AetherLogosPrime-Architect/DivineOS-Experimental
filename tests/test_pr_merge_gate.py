"""Tests for the pr_merge_gate doorman.

Per prereg-b6dcddd005b0. The gate fires on `gh pr merge` invocations
against guardrail-touching PRs that lack an External-Review trailer.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core import pr_merge_gate


class TestBlockReason:
    def test_non_bash_command_passes(self) -> None:
        assert pr_merge_gate.block_reason("") is None
        assert pr_merge_gate.block_reason("   ") is None

    def test_non_gh_pr_merge_passes(self) -> None:
        for cmd in [
            "git status",
            "ls -la",
            "gh pr view 42",
            "gh pr list",
            "gh pr create --title foo",
        ]:
            assert pr_merge_gate.block_reason(cmd) is None, cmd

    def test_pr_with_no_guardrail_touches_passes(self) -> None:
        with patch.object(
            pr_merge_gate, "audit_pr_for_guardrail_touches", return_value=(False, [])
        ):
            assert pr_merge_gate.block_reason("gh pr merge 99 --squash") is None

    def test_guardrail_pr_without_trailer_blocks(self) -> None:
        with patch.object(
            pr_merge_gate,
            "audit_pr_for_guardrail_touches",
            return_value=(True, ["src/divineos/core/moral_compass.py"]),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "BLOCKED" in reason
            assert "moral_compass.py" in reason
            assert "External-Review" in reason
            assert "pr-merge-check 99" in reason

    def test_guardrail_pr_with_trailer_in_body_passes(self) -> None:
        with patch.object(
            pr_merge_gate,
            "audit_pr_for_guardrail_touches",
            return_value=(True, ["src/divineos/core/moral_compass.py"]),
        ):
            cmd = 'gh pr merge 99 --squash --body "fix\n\nExternal-Review: round-abc123"'
            assert pr_merge_gate.block_reason(cmd) is None

    def test_gh_module_failure_fails_open(self) -> None:
        with patch.object(
            pr_merge_gate,
            "audit_pr_for_guardrail_touches",
            side_effect=RuntimeError("gh unavailable"),
        ):
            assert pr_merge_gate.block_reason("gh pr merge 99 --squash") is None

    def test_unparseable_pr_number_fails_open(self) -> None:
        # The regex requires \d+ so non-numeric PRs don't match; the
        # gate fails open rather than blocking on shapes it doesn't
        # recognize.
        assert pr_merge_gate.block_reason("gh pr merge feature-branch") is None


class TestGuardrailIntersection:
    def test_empty_file_list_returns_clean(self) -> None:
        with patch.object(pr_merge_gate, "_pr_files", return_value=None):
            touches, files = pr_merge_gate.audit_pr_for_guardrail_touches(99)
            assert touches is False
            assert files == []

    def test_intersection_only_returns_guardrail_files(self) -> None:
        # Two files in PR; only one is on the guardrail list.
        with (
            patch.object(
                pr_merge_gate,
                "_pr_files",
                return_value=[
                    "src/divineos/core/moral_compass.py",
                    "src/divineos/cli/audit_commands.py",
                ],
            ),
            patch.object(
                pr_merge_gate,
                "_load_guardrail_set",
                return_value={"src/divineos/core/moral_compass.py"},
            ),
        ):
            touches, files = pr_merge_gate.audit_pr_for_guardrail_touches(99)
            assert touches is True
            assert files == ["src/divineos/core/moral_compass.py"]

    def test_no_overlap_returns_clean(self) -> None:
        with (
            patch.object(
                pr_merge_gate,
                "_pr_files",
                return_value=["scripts/check_push_readiness.sh"],
            ),
            patch.object(
                pr_merge_gate,
                "_load_guardrail_set",
                return_value={"src/divineos/core/moral_compass.py"},
            ),
        ):
            touches, files = pr_merge_gate.audit_pr_for_guardrail_touches(99)
            assert touches is False
            assert files == []
