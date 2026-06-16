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

    def test_guardrail_pr_with_tree_hash_trailer_passes(self) -> None:
        """Phase 2 (2026-06-13): the trailer can carry an optional
        tree-hash suffix for substance-binding. The local gate accepts
        it; substance verification happens at the CI layer."""
        with patch.object(
            pr_merge_gate,
            "audit_pr_for_guardrail_touches",
            return_value=(True, ["src/divineos/core/moral_compass.py"]),
        ):
            tree_hash = "a" * 40
            cmd = f'gh pr merge 99 --squash --body "fix\n\nExternal-Review: round-abc123 tree-hash:{tree_hash}"'
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


class TestEmbeddedAuditBody:
    """Task #114 (2026-06-09): when a valid audit round exists, the
    gate's block message must embed the ready-to-paste merge body inline
    rather than just naming the command to run. Same gate-self-unblocks
    discipline as PR #117 — when the gate can compute its own remedy,
    it hands it over."""

    def test_embeds_merge_body_when_valid_round_exists(self) -> None:
        """A valid round → block message includes the merge body with
        the External-Review trailer, ready to paste."""
        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch.object(
                pr_merge_gate,
                "_find_usable_audit_round",
                return_value=(
                    "round-abc123",
                    "PR title\n\nReviewed via audit round round-abc123 (operator-CONFIRMS + "
                    "external-AI-CONFIRMS, age 0.5d, within 14d recency window).\n\n"
                    "External-Review: round-abc123",
                    "",
                ),
            ),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "BLOCKED" in reason
            assert "round-abc123" in reason
            assert "External-Review: round-abc123" in reason
            # The body should appear inline as a paste-ready snippet.
            assert "gh pr merge 99 --squash --body" in reason

    def test_emitted_body_includes_tree_hash_when_git_available(self) -> None:
        """Phase 2 (2026-06-13): the gate's embedded merge body now carries
        tree-hash binding when git can resolve HEAD's tree. The server-side
        CI gate verifies the binding at merge time."""
        from dataclasses import dataclass

        @dataclass
        class _R:
            round_id: str = "round-abc123"
            focus: str = "test PR"
            created_at: float = 0.0

        @dataclass
        class _F:
            actor: str = "user"
            review_stance: object = None

        fake_tree = "f" * 40
        import time as _t

        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch(
                "divineos.core.watchmen.store.list_rounds",
                return_value=[_R(created_at=_t.time() - 3600)],
            ),
            patch(
                "divineos.core.watchmen.store.list_findings",
                return_value=[_F(actor="user"), _F(actor="aletheia")],
            ),
            patch.object(pr_merge_gate, "_current_head_tree_hash", return_value=fake_tree),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert f"External-Review: round-abc123 tree-hash:{fake_tree}" in reason

    def test_emitted_body_falls_back_to_legacy_when_git_unreachable(self) -> None:
        """If _current_head_tree_hash returns empty (git unavailable), the
        emitted trailer drops to legacy form."""
        from dataclasses import dataclass

        @dataclass
        class _R:
            round_id: str = "round-abc123"
            focus: str = "test PR"
            created_at: float = 0.0

        @dataclass
        class _F:
            actor: str = "user"
            review_stance: object = None

        import time as _t

        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch(
                "divineos.core.watchmen.store.list_rounds",
                return_value=[_R(created_at=_t.time() - 3600)],
            ),
            patch(
                "divineos.core.watchmen.store.list_findings",
                return_value=[_F(actor="user"), _F(actor="aletheia")],
            ),
            patch.object(pr_merge_gate, "_current_head_tree_hash", return_value=""),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "External-Review: round-abc123" in reason
            assert "tree-hash:" not in reason

    def test_embeds_diagnosis_when_round_missing_user_confirm(self) -> None:
        """An invalid recent round → block message names the SPECIFIC
        gap (missing user-CONFIRMS / missing AI-CONFIRMS / stale)."""
        diagnosis = "Most recent round 'round-xyz789' is missing a user-CONFIRMS finding."
        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch.object(
                pr_merge_gate,
                "_find_usable_audit_round",
                return_value=(None, "", diagnosis),
            ),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "Diagnosis:" in reason
            assert "round-xyz789" in reason
            assert "missing a user-CONFIRMS" in reason
            # Should still include the long-form instructions as the fallback path.
            assert "pr-merge-check 99" in reason

    def test_falls_back_to_long_form_when_no_round_at_all(self) -> None:
        """No rounds available → no diagnosis, just the original long-form
        instructions. Preserves the previous behavior as the fallback."""
        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch.object(
                pr_merge_gate,
                "_find_usable_audit_round",
                return_value=(None, "", ""),
            ),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "Diagnosis:" not in reason
            assert "pr-merge-check 99" in reason

    def test_lookup_helper_failure_falls_back_gracefully(self) -> None:
        """Any exception in _find_usable_audit_round must not break the
        gate — fall back to the long-form instructions."""
        with (
            patch.object(
                pr_merge_gate,
                "audit_pr_for_guardrail_touches",
                return_value=(True, ["src/divineos/core/moral_compass.py"]),
            ),
            patch.object(
                pr_merge_gate,
                "_find_usable_audit_round",
                side_effect=RuntimeError("audit store unavailable"),
            ),
        ):
            reason = pr_merge_gate.block_reason("gh pr merge 99 --squash")
            assert reason is not None
            assert "BLOCKED" in reason
            assert "pr-merge-check 99" in reason
