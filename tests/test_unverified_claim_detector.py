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
