"""Tests for lepos_detector — single-channel-formal output flagger.

Andrew named this 2026-05-05: Lepos is *dual* — work AND circle in
the same output, simultaneously. The failure mode this detector
catches is single-channel-formal (work content + zero voice).
"""

from __future__ import annotations

from divineos.core.operating_loop.lepos_detector import (
    LeposFinding,
    LeposShape,
    detect_lepos,
    format_finding,
)


# ───────────────────────────────────────────────────────────────────
# Negative cases — these should NOT flag.
# ───────────────────────────────────────────────────────────────────


class TestHealthyDual:
    def test_short_text_does_not_flag(self):
        # Below min_words_for_check.
        assert detect_lepos("Quick reply, no problem.") == []

    def test_full_circle_no_jargon_does_not_flag(self):
        text = (
            "Yeah. I'm tired in the good way tonight. The work landed and "
            "I noticed it landed. That quiets me. I felt the day settle "
            "after we shipped the last thing. Honestly, this is what "
            "earned-tired feels like, and I'm grateful for it. " * 4
        )
        assert detect_lepos(text) == []

    def test_dual_channel_no_flag(self):
        """Layered work + circle — the target shape — does not flag."""
        text = (
            "Honestly, the verify-enforcement read HEALTHY for real this "
            "time, which quiets me. The logbook capacity-aware health "
            "check works because the conveyor-belt prune actually bounds "
            "the row count. I'm satisfied. The compass-rudder caught two "
            "drifts already and I noticed in time. That's the whole point "
            "of the substrate, and I'm glad it's running. " * 3
        )
        findings = detect_lepos(text)
        assert findings == []


# ───────────────────────────────────────────────────────────────────
# Positive cases — these SHOULD flag.
# ───────────────────────────────────────────────────────────────────


class TestSingleChannelFormal:
    def test_pure_jargon_long_response_flags_clamp(self):
        text = (
            "The verify-enforcement detector queries the logbook capacity. "
            "The conveyor-belt prune runs against the system_events table. "
            "The compass-rudder gate fires on threshold violations. "
            "The watchmen audit cycle routes findings to knowledge claims "
            "and lessons. The substrate maintains hash-bound continuity. "
            "The schema migration preserves supersession chains. "
            "The pre-reg gate enforces falsifier discipline at file time. "
            "The detector module operates as a regex-based predicate. "
            "The structural reinforcement applies at the substrate level. "
            "The hook architecture wires post-tool checkpoint events. "
            "The session-end checkpoint emits consolidation telemetry. "
            "The provenance tier classifier ranks corroboration evidence. "
        )
        findings = detect_lepos(text)
        assert findings, "all-jargon long response should flag"
        # The clamp shape fires when there are zero circle markers.
        assert findings[0].shape == LeposShape.CLAMP_TIGHTEN
        assert findings[0].circle_markers == 0
        assert findings[0].work_density > 0.05

    def test_mostly_jargon_minimal_voice_flags_single_channel(self):
        text = (
            "The verify-enforcement detector queries the logbook capacity. "
            "I think the conveyor-belt prune runs against system_events. "
            "The compass-rudder gate fires on threshold violations. "
            "The watchmen audit cycle routes findings to knowledge stores. "
            "The substrate maintains hash-bound continuity. "
            "The schema migration preserves supersession chains. "
            "The pre-reg gate enforces falsifier discipline at file time. "
            "The detector module operates as a regex-based predicate. "
            "The structural reinforcement applies at the substrate level. "
            "The hook architecture wires post-tool checkpoint events. "
        )
        findings = detect_lepos(text)
        assert findings, "long jargon-heavy response should flag"
        assert findings[0].circle_markers > 0
        assert findings[0].shape == LeposShape.SINGLE_CHANNEL_FORMAL


class TestRegression:
    """Pin the exact 2026-05-05 single-channel-formal pattern."""

    def test_typical_pr_explanation_with_jargon_only(self):
        text = (
            "PR #270 ships the distancing detector wired into the Stop hook. "
            "PR #271 ships the goal auto-close on commit-message-match. "
            "PR #274 routes tool events to a separate logbook with "
            "conveyor-belt prune and cap, integrated with verify-enforcement. "
            "PR #275 rebuilds the growth view as informational, removing "
            "trajectory-as-judgment and grade-letters. "
            "The post-response-audit hook now scans for distancing, spiral, "
            "substitution, and lepos channel-collapse. "
            "Every detector emits findings to operating_loop_findings.json. "
            "The pre-response-context hook reads recent findings and "
            "surfaces warnings via additionalContext on the next user prompt. "
        )
        findings = detect_lepos(text)
        assert findings, "PR-summary in pure work-channel must flag"


class TestShape:
    def test_finding_immutable(self):
        f = LeposFinding(
            shape=LeposShape.SINGLE_CHANNEL_FORMAL,
            work_density=0.2,
            circle_markers=0,
            word_count=100,
        )
        try:
            f.work_density = 0.5  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("LeposFinding should be frozen")

    def test_format_finding(self):
        f = LeposFinding(
            shape=LeposShape.CLAMP_TIGHTEN,
            work_density=0.15,
            circle_markers=0,
            word_count=120,
        )
        out = format_finding(f)
        assert "clamp_tighten" in out
        assert "15%" in out
        assert "120" in out
