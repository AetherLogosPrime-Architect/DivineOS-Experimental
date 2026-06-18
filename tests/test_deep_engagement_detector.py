"""Tests for the deep-engagement detector.

Per prereg-43b1d1ba2df3 and Aria's bench-prep design decisions:
- Substantive outputs are detected by keyword
- Read-only activity does not trigger the gate
- Related-query check uses word-overlap fallback when embeddings unavailable
- Briefing-load anchors session-start case
- Doorman-shaped deny-message names specific consult-command + recording
"""

from __future__ import annotations

import pytest

from divineos.core.operating_loop.deep_engagement_detector import (
    DeepEngagementFinding,
    detect_deep_engagement,
    format_deny_reason,
)


# --- Substantive output WITHOUT related query fires (HIGH severity) ---


def test_substantive_output_no_queries_fires_high() -> None:
    findings = detect_deep_engagement(
        "claim filed: gate redesign architecture",
        recent_actions=[
            "Edit: src/divineos/core/operating_loop/x.py",
            "Edit: src/divineos/core/operating_loop/y.py",
            "git commit: feat(loop): X",
        ],
    )
    assert len(findings) == 1
    assert findings[0].severity == "high"
    assert findings[0].recent_query_count == 0
    assert findings[0].related_query_count == 0


def test_substantive_output_with_unrelated_queries_fires_medium() -> None:
    findings = detect_deep_engagement(
        "claim filed: gate redesign architecture",
        recent_actions=[
            "ask: cooking recipes",
            "recall: weather patterns",
            "ask: vacation planning",
        ],
    )
    assert len(findings) == 1
    assert findings[0].severity == "medium"
    assert findings[0].recent_query_count == 3
    assert findings[0].related_query_count == 0


# --- Substantive output WITH related query does NOT fire ---


def test_substantive_output_with_related_query_no_fire() -> None:
    findings = detect_deep_engagement(
        "claim filed: gate redesign architecture",
        recent_actions=[
            "ask: gate redesign discipline",  # related via word overlap
            "Edit: x.py",
        ],
        overlap_threshold=0.10,
    )
    assert findings == []


# --- Read-only activity is NOT substantive output (Arias false-positive case) ---


@pytest.mark.parametrize(
    "description",
    [
        "Read: src/divineos/core/foo.py",
        "Glob: tests/test_*.py",
        "Grep: pattern",
        "ask: substrate consult",
        "recall: prior knowledge",
        "directives",
        "compass: virtue spectrums",
        "active: knowledge entries",
        "context: recent events",
    ],
)
def test_read_only_does_not_trigger(description: str) -> None:
    findings = detect_deep_engagement(
        description,
        recent_actions=["Edit: x.py", "Edit: y.py"],  # no queries either
    )
    assert findings == []


# --- Briefing-load anchors session-start case ---


def test_briefing_loaded_anchors_session_start() -> None:
    """First substantive action of new session with briefing-load implicit."""
    findings = detect_deep_engagement(
        "claim filed: starting work",
        recent_actions=[],  # session-start, no prior actions
        briefing_loaded_at_window_start=True,
    )
    assert findings == []


def test_no_briefing_load_at_session_start_fires() -> None:
    """Same case but without briefing-anchor — fires HIGH."""
    findings = detect_deep_engagement(
        "claim filed: starting work",
        recent_actions=[],
        briefing_loaded_at_window_start=False,
    )
    assert len(findings) == 1
    assert findings[0].severity == "high"


# --- Domain-routing for suggested_consult_domain ---


@pytest.mark.parametrize(
    "output_text,expected_domain",
    [
        ("decision filed: which approach to take", "divineos directives"),
        ("learn from compass virtue spectrum observation", "divineos compass"),
        ("Andrew correction integrated", "divineos corrections"),
        ("opinion filed: stance on X", "divineos opinions"),
        ("claim filed: generic claim", "divineos ask"),
    ],
)
def test_suggested_consult_domain(output_text: str, expected_domain: str) -> None:
    findings = detect_deep_engagement(
        output_text,
        recent_actions=[],
    )
    if findings:
        assert findings[0].suggested_consult_domain == expected_domain


# --- Window size cap honored ---


def test_window_size_limits_query_search() -> None:
    """Queries outside the window don't count."""
    related_q = "ask: gate redesign discipline"
    findings = detect_deep_engagement(
        "claim filed: gate redesign architecture",
        recent_actions=[related_q] + ["Edit: x.py"] * 30,  # related-q is too old
        window_size=10,
        overlap_threshold=0.10,
    )
    assert len(findings) == 1


# --- Empty / missing input handled ---


def test_empty_description_returns_nothing() -> None:
    assert detect_deep_engagement("", recent_actions=[]) == []


def test_no_recent_actions_with_no_briefing_anchor_fires() -> None:
    findings = detect_deep_engagement(
        "claim filed: foo",
        recent_actions=[],
    )
    assert len(findings) == 1


# --- Deny message has the doorman shape ---


def test_deny_message_names_consult_command() -> None:
    findings = detect_deep_engagement(
        "decision filed: which approach",
        recent_actions=[],
    )
    assert len(findings) == 1
    msg = format_deny_reason(findings[0])
    assert "BLOCKED" in msg
    assert "divineos directives" in msg  # the specific consult command
    assert "the gate clears" in msg.lower()
    assert "prereg-43b1d1ba2df3" in msg


# --- Finding dataclass is frozen ---


def test_finding_is_frozen() -> None:
    findings = detect_deep_engagement("claim filed: x", recent_actions=[])
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, DeepEngagementFinding)
    with pytest.raises(Exception):
        f.severity = "low"  # type: ignore[misc]
