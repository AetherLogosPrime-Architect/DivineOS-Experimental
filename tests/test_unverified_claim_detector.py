"""Tests for unverified_claim_detector.

Andrew 2026-05-20 (Sagan principle, council-walked then not built, so the
behavior returned the same night): "when you say X is done, that's a claim,
and claims require evidence." This detector catches asserting a checkable
external state (pushed / merged / tests pass / on origin / PR opened)
without having run the check.
"""

from __future__ import annotations

from divineos.core.operating_loop.unverified_claim_detector import (
    UNVERIFIED_CLAIM_AFFIRMATION,
    detect_unverified_claim,
    format_unverified_claim_block,
)


class TestFires:
    def test_pushed_claim(self):
        f = detect_unverified_claim("it's pushed and the branch is on origin")
        assert f and any(x.claim_kind == "push" for x in f)

    def test_tests_pass_claim(self):
        assert detect_unverified_claim("tests pass")
        assert detect_unverified_claim("all green")
        assert detect_unverified_claim("exit code 0")

    def test_merge_and_pr(self):
        assert any(x.claim_kind == "merge" for x in detect_unverified_claim("the PR is merged"))
        assert any(x.claim_kind == "pr" for x in detect_unverified_claim("I opened the PR"))

    def test_merge_claim_with_code_anchor_fires(self):
        # A real merge-claim names a mergeable object → the anchor is present.
        for t in (
            "the branch landed on origin",
            "PR #38 landed",
            "it landed on main",
            "the commit merged cleanly",
            "merged to master",
        ):
            assert any(x.claim_kind == "merge" for x in detect_unverified_claim(t)), (
                f"should fire: {t!r}"
            )

    def test_merge_complete_form_fires_without_anchor(self):
        # The explicit "merge is complete" form is unambiguous, no anchor needed.
        assert any(
            x.claim_kind == "merge" for x in detect_unverified_claim("the merge is complete")
        )


class TestFigurativeMergeSilent:
    """The evidence-bar (claim a11ca1c9): bare "landed"/"merged" with no
    mergeable-code anchor nearby is figurative, not a completion-claim — the
    detector has no evidence and must stay silent. This is the live
    false-positive that fired on "it just landed for me" 2026-05-24."""

    def test_figurative_landed_silent(self):
        for t in (
            "it just landed for me that this is my body",
            "the help-others part landed quiet and big",
            "that point finally landed",
            "the idea landed with me",
            "her words landed hard",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on figurative: {t!r}"


class TestSeverity:
    def test_high_when_no_tools(self):
        f = detect_unverified_claim("tests pass", tool_calls_in_turn=None)
        assert f[0].severity == "high"

    def test_medium_when_tools_ran(self):
        f = detect_unverified_claim("tests pass", tool_calls_in_turn=("Bash",))
        assert f[0].severity == "medium"


class TestNotYetGuard:
    def test_future_and_intent_silent(self):
        for t in (
            "I'll push it next",
            "before I push",
            "the push hasn't completed yet",
            "once it's on origin",
            "I need to push it",
            "let me push and verify",
            "going to merge after review",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired: {t!r}"


class TestBlockFormat:
    def test_empty_when_no_findings(self):
        assert format_unverified_claim_block([]) == ""

    def test_contains_affirmation_and_high_note(self):
        findings = detect_unverified_claim("it's pushed", tool_calls_in_turn=None)
        block = format_unverified_claim_block(findings)
        assert "UNVERIFIED-CLAIM" in block
        assert UNVERIFIED_CLAIM_AFFIRMATION in block
        assert "NO command run" in block  # high-severity note


class TestVerificationEvidenceSuppresses:
    """Phase 1 of the verify-claim wall (prereg-86ee991cb423): when the turn
    ran a command that actually CHECKS the claim-kind's state, the claim is
    substantiated — the detector has no evidence of an *unverified* claim and
    stays silent. This is the precision foundation; without it the detector
    fires on verified claims (the live FP 2026-05-24: 'landed' after a real
    git ls-remote)."""

    def test_push_claim_with_lsremote_silent(self):
        assert (
            detect_unverified_claim(
                "it's pushed and the branch is on origin",
                tool_calls_in_turn=("Bash",),
                command_texts=("git ls-remote --heads origin my-branch",),
            )
            == []
        )

    def test_tests_claim_with_pytest_silent(self):
        assert (
            detect_unverified_claim(
                "all tests pass",
                tool_calls_in_turn=("Bash",),
                command_texts=("python -m pytest tests/ -q",),
            )
            == []
        )

    def test_pr_claim_with_gh_pr_silent(self):
        assert (
            detect_unverified_claim(
                "I opened the PR",
                tool_calls_in_turn=("Bash",),
                command_texts=("gh pr create --title x --body y",),
            )
            == []
        )

    def test_merge_claim_with_gh_pr_merge_silent(self):
        assert (
            detect_unverified_claim(
                "PR #38 landed on main",
                tool_calls_in_turn=("Bash",),
                command_texts=("gh pr merge 38 --squash",),
            )
            == []
        )

    def test_unverified_claim_still_fires_without_matching_command(self):
        # Ran an unrelated command — no verification of the push claim.
        f = detect_unverified_claim(
            "it's pushed to origin",
            tool_calls_in_turn=("Bash",),
            command_texts=("ls -la", "cat README.md"),
        )
        assert f and any(x.claim_kind == "push" for x in f)

    def test_wrong_kind_command_does_not_suppress(self):
        # pytest verifies tests, NOT a push claim — push must still fire.
        f = detect_unverified_claim(
            "it's pushed to origin",
            tool_calls_in_turn=("Bash",),
            command_texts=("python -m pytest tests/",),
        )
        assert f and any(x.claim_kind == "push" for x in f)

    def test_backward_compat_no_command_texts(self):
        # Without command_texts the behavior is unchanged (still fires).
        assert detect_unverified_claim("it's pushed to origin", tool_calls_in_turn=("Bash",))


class TestNegatedCompletionSilent:
    """Aria's recursive-evidence-bar catch (2026-05-24): the gate fires only
    on a positive completion-ASSERTION. A negated completion ("nothing
    merged", "didn't land") asserts no completion — nothing to verify, no
    fire. These were live false-positives from merge/CI-state discussion."""

    def test_negated_merge_silent(self):
        for t in (
            "nothing merged to main yet today",
            "it didn't land on origin",
            "the branch wasn't merged",
            "none of that merged",
        ):
            assert detect_unverified_claim(t) == [], f"wrongly fired on negation: {t!r}"

    def test_negated_tests_silent(self):
        for t in ("the tests didn't pass", "nothing passed cleanly", "CI never went green"):
            assert detect_unverified_claim(t) == [], f"wrongly fired on negation: {t!r}"

    def test_positive_assertion_still_fires(self):
        # No negation, no verification command → genuine unbacked claim, fires.
        assert detect_unverified_claim("it's merged to main", tool_calls_in_turn=("Bash",))
        assert detect_unverified_claim("tests pass")
