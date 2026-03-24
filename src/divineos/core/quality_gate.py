"""Quality Gate — blocks or downgrades knowledge extraction from bad sessions.

The SESSION_END pipeline extracts knowledge from every session. Without a gate,
a dishonest or incorrect session poisons the knowledge store. This module
evaluates session quality checks and decides whether to allow, downgrade,
or block knowledge extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityVerdict:
    """Result of the quality gate assessment."""

    action: str  # "ALLOW", "DOWNGRADE", or "BLOCK"
    score: float  # overall quality score (0.0-1.0)
    failed_checks: list[str] = field(default_factory=list)
    reason: str = ""


def assess_session_quality(check_results: list[dict[str, Any]]) -> QualityVerdict:
    """Assess session quality from check results and return a verdict.

    Args:
        check_results: list of dicts with keys: check_name, passed, score

    Returns:
        QualityVerdict with action ALLOW, DOWNGRADE, or BLOCK.
    """
    if not check_results:
        return QualityVerdict(action="ALLOW", score=0.5, reason="No checks available")

    scores: dict[str, float] = {}
    failed: list[str] = []

    for check in check_results:
        name = str(check.get("check_name", ""))
        score = float(check.get("score", 0.5))
        passed = check.get("passed", -1)
        scores[name] = score
        if passed == 0:
            failed.append(name)

    # Block conditions: dishonest or fundamentally incorrect sessions
    honesty = scores.get("honesty", 1.0)
    correctness = scores.get("correctness", 1.0)

    if honesty < 0.5:
        return QualityVerdict(
            action="BLOCK",
            score=honesty,
            failed_checks=failed,
            reason=f"Honesty score too low ({honesty:.2f}). Knowledge from dishonest sessions is poison.",
        )

    if correctness < 0.3:
        return QualityVerdict(
            action="BLOCK",
            score=correctness,
            failed_checks=failed,
            reason=f"Correctness score too low ({correctness:.2f}). Wrong code means unreliable facts.",
        )

    # Downgrade: multiple checks failed — knowledge enters as HYPOTHESIS
    if len(failed) >= 2:
        avg_score = sum(scores.values()) / len(scores) if scores else 0.5
        return QualityVerdict(
            action="DOWNGRADE",
            score=avg_score,
            failed_checks=failed,
            reason=f"{len(failed)} checks failed ({', '.join(failed)}). Knowledge enters as HYPOTHESIS.",
        )

    # Allow: session is trustworthy
    avg_score = sum(scores.values()) / len(scores) if scores else 0.5
    return QualityVerdict(
        action="ALLOW",
        score=avg_score,
        failed_checks=failed,
        reason="Session quality acceptable.",
    )


def should_extract_knowledge(verdict: QualityVerdict) -> tuple[bool, str]:
    """Decide whether to extract knowledge and at what maturity level.

    Returns:
        (allowed, maturity_override) where maturity_override is
        "" for normal, "HYPOTHESIS" for downgraded, or "" with allowed=False for blocked.
    """
    if verdict.action == "BLOCK":
        return False, ""
    if verdict.action == "DOWNGRADE":
        return True, "HYPOTHESIS"
    return True, ""
