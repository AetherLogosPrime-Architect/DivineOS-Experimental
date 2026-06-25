"""Tests for divineos.core.pr_gate.

Focus: deterministic parser/decision logic (is_gh_pr_create,
has_draft_flag, check_pr_create_safe routing). The
branch_files_changed and load_guardrail_set helpers wrap git/IO
and are integration-tested via the live hook.
"""

from __future__ import annotations

from unittest.mock import patch

from divineos.core.pr_gate import (
    GateDecision,
    check_pr_create_safe,
    has_draft_flag,
    is_gh_pr_create,
)


class TestIsGhPrCreate:
    """Match `gh pr create` as a discrete subcommand sequence."""

    def test_bare_invocation(self):
        assert is_gh_pr_create("gh pr create") is True

    def test_with_title_flag(self):
        assert is_gh_pr_create("gh pr create --title 'fix'") is True

    def test_with_draft_flag(self):
        assert is_gh_pr_create("gh pr create --draft") is True

    def test_in_pipeline(self):
        assert is_gh_pr_create("echo x | gh pr create --title 'fix'") is True

    def test_not_a_create_subcommand(self):
        # `gh pr create-comment` is a different verb.
        assert is_gh_pr_create("gh pr create-comment") is False

    def test_not_a_gh_pr(self):
        assert is_gh_pr_create("gh issue create") is False

    def test_empty_string(self):
        assert is_gh_pr_create("") is False

    def test_unrelated_command(self):
        assert is_gh_pr_create("git push origin main") is False


class TestHasDraftFlag:
    """`--draft` and `-d` as standalone flags."""

    def test_long_draft_flag(self):
        assert has_draft_flag("gh pr create --draft") is True

    def test_short_draft_flag(self):
        assert has_draft_flag("gh pr create -d") is True

    def test_draft_in_middle(self):
        assert has_draft_flag("gh pr create --title 'x' --draft --body 'y'") is True

    def test_no_draft_flag(self):
        assert has_draft_flag("gh pr create --title 'fix'") is False

    def test_draft_in_quoted_string_not_flag(self):
        # `--draft-something` would not be standalone; this is the boundary case.
        assert has_draft_flag("gh pr create --title 'draft notes'") is False

    def test_d_in_other_word_not_flag(self):
        # `-draft` (one dash) is not the short flag.
        assert has_draft_flag("gh pr create -draft") is False


class TestCheckPrCreateSafeRouting:
    """The central allow/block decision, isolated from git/IO."""

    def test_non_gh_pr_create_allowed(self):
        decision = check_pr_create_safe("ls -la")
        assert decision.blocked is False
        assert decision.reason == ""

    def test_already_draft_allowed(self):
        decision = check_pr_create_safe("gh pr create --draft --title 'x'")
        assert decision.blocked is False

    def test_already_draft_short_flag_allowed(self):
        decision = check_pr_create_safe("gh pr create -d --title 'x'")
        assert decision.blocked is False

    def test_no_branch_changes_allowed(self):
        # Mock empty branch diff — no files to gate.
        with patch("divineos.core.pr_gate.branch_files_changed", return_value=[]):
            decision = check_pr_create_safe("gh pr create --title 'fix'")
            assert decision.blocked is False

    def test_no_guardrail_overlap_allowed(self):
        # Branch touches files but none are on the guardrail list.
        with (
            patch(
                "divineos.core.pr_gate.branch_files_changed",
                return_value=["src/foo.py", "tests/test_foo.py"],
            ),
            patch(
                "divineos.core.pr_gate.load_guardrail_set",
                return_value={"docs/sacred.md"},
            ),
        ):
            decision = check_pr_create_safe("gh pr create --title 'fix'")
            assert decision.blocked is False

    def test_guardrail_touched_without_draft_blocked(self):
        with (
            patch(
                "divineos.core.pr_gate.branch_files_changed",
                return_value=["src/foo.py", "docs/sacred.md"],
            ),
            patch(
                "divineos.core.pr_gate.load_guardrail_set",
                return_value={"docs/sacred.md"},
            ),
        ):
            decision = check_pr_create_safe("gh pr create --title 'fix'")
            assert decision.blocked is True
            assert decision.touched_guardrails == ["docs/sacred.md"]
            assert "guardrail file(s)" in decision.reason
            assert "Add --draft" in decision.reason

    def test_guardrail_touched_with_draft_allowed(self):
        with (
            patch(
                "divineos.core.pr_gate.branch_files_changed",
                return_value=["src/foo.py", "docs/sacred.md"],
            ),
            patch(
                "divineos.core.pr_gate.load_guardrail_set",
                return_value={"docs/sacred.md"},
            ),
        ):
            decision = check_pr_create_safe("gh pr create --draft --title 'fix'")
            assert decision.blocked is False

    def test_empty_guardrail_file_fails_open(self):
        # If we can't read the guardrail list, we fail-open (allow).
        with (
            patch(
                "divineos.core.pr_gate.branch_files_changed",
                return_value=["docs/sacred.md"],
            ),
            patch("divineos.core.pr_gate.load_guardrail_set", return_value=set()),
        ):
            decision = check_pr_create_safe("gh pr create --title 'fix'")
            assert decision.blocked is False

    def test_block_message_truncates_long_guardrail_list(self):
        many = [f"docs/file{i}.md" for i in range(10)]
        with (
            patch(
                "divineos.core.pr_gate.branch_files_changed",
                return_value=many,
            ),
            patch(
                "divineos.core.pr_gate.load_guardrail_set",
                return_value=set(many),
            ),
        ):
            decision = check_pr_create_safe("gh pr create --title 'fix'")
            assert decision.blocked is True
            assert len(decision.touched_guardrails or []) == 10
            # Reason shows first 5 with "..." overflow marker.
            assert "..." in decision.reason


class TestGateDecisionDataclass:
    """The result type is well-formed for both allow and block."""

    def test_allow_default_shape(self):
        d = GateDecision(blocked=False)
        assert d.blocked is False
        assert d.reason == ""
        assert d.touched_guardrails is None

    def test_block_shape(self):
        d = GateDecision(blocked=True, reason="why", touched_guardrails=["a"])
        assert d.blocked is True
        assert d.reason == "why"
        assert d.touched_guardrails == ["a"]
