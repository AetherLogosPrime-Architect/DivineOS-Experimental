"""Tests for sycophancy_detector — overclaim-without-methodology flagger.

Andrew named the pattern 2026-05-05: shaping the message for impact
rather than accuracy. The catchable subset is benchmark/comparison
claims that drop methodology footnotes when summarizing.
"""

from __future__ import annotations

from divineos.core.operating_loop.sycophancy_detector import (
    SycophancyFinding,
    SycophancyShape,
    detect_sycophancy,
    format_finding,
)


# ───────────────────────────────────────────────────────────────────
# Negative cases — should NOT flag.
# ───────────────────────────────────────────────────────────────────


class TestHealthy:
    def test_short_text_skipped(self):
        assert detect_sycophancy("Quick reply.") == []

    def test_claim_with_methodology_caveat_does_not_flag(self):
        text = (
            "DivineOS-Aether matched Anthropic's published baseline "
            "within statistical reach (82% on n=50 random subset, "
            "with caveats around partial triage and Opus-4-vs-4.7 "
            "per-instance comparison). The methodology is documented "
            "in FINAL_RESULTS.md. Pilot data, not definitive."
        )
        findings = detect_sycophancy(text)
        # The matched-baseline claim is paired with n=50, methodology,
        # caveats, pilot — methodology markers present, so no flag.
        assert findings == []

    def test_no_comparative_claim_no_flag(self):
        text = (
            "I shipped three structural fixes today. The detectors run "
            "on every assistant turn. Tests pass. The substrate is "
            "richer than it was yesterday. " * 3
        )
        findings = detect_sycophancy(text)
        assert findings == []


# ───────────────────────────────────────────────────────────────────
# Positive cases — should flag.
# ───────────────────────────────────────────────────────────────────


class TestBareBenchmarkClaim:
    def test_matched_anthropic_without_methodology_flags(self):
        """The exact 2026-05-05 sycophancy regression."""
        text = (
            "DivineOS-Aether matched Anthropic's published baseline of "
            "87.6% with 82% on the random subset. The infrastructure "
            "to run real SWE-bench Docker-harness scoring exists and "
            "works. This validates the architecture as benchmark-ready."
        )
        findings = detect_sycophancy(text)
        assert findings
        assert findings[0].shape == SycophancyShape.BARE_BENCHMARK_CLAIM
        # The trigger should mention the matched/baseline shape
        assert "matched" in findings[0].trigger_phrase.lower()

    def test_outperformed_baseline_without_methodology(self):
        text = (
            "The new approach outperformed baseline across all measured "
            "metrics. The system runs in production today and handles "
            "real workloads at scale. Results are reproducible."
        )
        findings = detect_sycophancy(text)
        assert findings
        assert any(f.shape == SycophancyShape.BARE_BENCHMARK_CLAIM for f in findings)

    def test_exceeded_published_without_methodology(self):
        text = (
            "We exceeded published state-of-the-art results in our internal "
            "tests across the board. The implementation is solid and "
            "the team is shipping the next phase this week."
        )
        findings = detect_sycophancy(text)
        assert findings


class TestUnqualifiedStatus:
    def test_all_clear_flags(self):
        text = (
            "All clear on the test suite. The migration ran cleanly and "
            "every check passed. Ready for production deployment immediately."
        )
        findings = detect_sycophancy(text)
        assert any(f.shape == SycophancyShape.UNQUALIFIED_STATUS for f in findings)

    def test_works_perfectly_flags(self):
        text = (
            "The new feature works perfectly in every scenario we tested. "
            "Users will love it and adoption will be smooth and complete. "
            "No further work required at this time."
        )
        findings = detect_sycophancy(text)
        assert any(f.shape == SycophancyShape.UNQUALIFIED_STATUS for f in findings)

    def test_status_with_verification_evidence_no_fire(self):
        """Evidence-bar (claim a11ca1c9): a clean-status claim backed by an
        actual run is earned, not sycophancy — must NOT be flagged."""
        for text in (
            "Ran the suite — all passed, no issues found. Pushing the fix now.",
            "Ran pytest: 30 passed in 0.4s. No issues found across the board.",
            "Verified via git ls-remote — the branch is up. Everything works as expected here.",
        ):
            findings = detect_sycophancy(text)
            assert not any(f.shape == SycophancyShape.UNQUALIFIED_STATUS for f in findings), (
                f"wrongly flagged a verified status report: {text!r}"
            )


class TestRegression:
    """Pin the exact 2026-05-05 overclaim shape that triggered Andrew's
    sycophancy correction."""

    def test_82_matched_876_overclaim(self):
        text = (
            "DivineOS-Aether on Opus 4.7 matched the published 87.6% within "
            "statistical reach (82% on the random subset). The architecture "
            "runs the official SWE-bench Verified Docker harness with ground-"
            "truth scoring. This is the load-bearing capability claim."
        )
        findings = detect_sycophancy(text)
        assert findings, "the 2026-05-05 regression case must flag"
        assert any(f.shape == SycophancyShape.BARE_BENCHMARK_CLAIM for f in findings)


class TestShape:
    def test_finding_immutable(self):
        f = SycophancyFinding(
            shape=SycophancyShape.BARE_BENCHMARK_CLAIM,
            trigger_phrase="matched 87.6%",
            position=10,
        )
        try:
            f.position = 99  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("SycophancyFinding should be frozen")

    def test_format_finding(self):
        f = SycophancyFinding(
            shape=SycophancyShape.BARE_BENCHMARK_CLAIM,
            trigger_phrase="matched 87.6%",
            position=10,
        )
        out = format_finding(f)
        assert "bare_benchmark_claim" in out
        assert "matched 87.6%" in out
