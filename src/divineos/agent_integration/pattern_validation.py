"""Pattern validation: invalidation detection, conflict detection, and humility audits."""

from typing import Any

from loguru import logger

from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.decision_store import DecisionStore


def detect_invalidation(
    pattern_store: PatternStore,
    *,
    failure_threshold: int = 3,
    confidence_archive_threshold: float = -0.5,
) -> list[str]:
    """Detect and archive failed/outdated patterns.

    Archives patterns that failed 3+ times (tactical) or have confidence < -0.5.
    """
    archived_patterns = []

    all_patterns = pattern_store.get_all_patterns()

    for pattern in all_patterns:
        pattern_id = pattern.get("pattern_id", "")
        if not pattern_id:
            continue
        confidence = pattern.get("confidence", 0.0)
        pattern_type = pattern.get("pattern_type")

        should_archive = False
        reason = ""
        delta = 0.0

        if confidence < confidence_archive_threshold:
            should_archive = True
            reason = f"Anti-pattern (confidence: {confidence:.2f})"
            delta = -0.5 - confidence

        if pattern_type == "tactical":
            successes = pattern.get("successes", 0)
            occurrences = pattern.get("occurrences", 0)
            failures = occurrences - successes

            if failures >= failure_threshold:
                should_archive = True
                reason = f"Tactical pattern failed {failures} times"
                delta = -0.5 - confidence

        if should_archive:
            pattern_store.update_pattern_confidence(
                pattern_id=pattern_id,
                delta=delta,
                reason=f"Archived: {reason}",
                _cached_pattern=pattern,
            )
            archived_patterns.append(pattern_id)
            logger.info(f"Archived pattern {pattern_id}: {reason}")

    return archived_patterns


def detect_conflicts(pattern_store: PatternStore) -> list[dict[str, Any]]:
    """Detect contradictory structural patterns with confidence > 0.6."""
    conflicts: list[dict[str, Any]] = []

    all_patterns = pattern_store.get_all_patterns()
    structural_patterns = [p for p in all_patterns if p.get("pattern_type") == "structural"]

    for i, pattern1 in enumerate(structural_patterns):
        for pattern2 in structural_patterns[i + 1 :]:
            prec1 = pattern1.get("preconditions", {})
            prec2 = pattern2.get("preconditions", {})

            for key in prec1:
                if key in prec2 and prec1[key] != prec2[key]:
                    conf1 = pattern1.get("confidence", 0.0)
                    conf2 = pattern2.get("confidence", 0.0)

                    if conf1 > 0.6 and conf2 > 0.6:
                        conflicts.append(
                            {
                                "pattern_id_1": pattern1.get("pattern_id"),
                                "pattern_id_2": pattern2.get("pattern_id"),
                                "conflict_reason": (
                                    f"Contradictory precondition '{key}': "
                                    f"{prec1[key]} vs {prec2[key]}"
                                ),
                            }
                        )
                        logger.warning(
                            f"Conflict detected between patterns "
                            f"{pattern1.get('pattern_id')} and "
                            f"{pattern2.get('pattern_id')}: {key}"
                        )

    return conflicts


def generate_humility_audit(
    pattern_store: PatternStore,
    decision_store: DecisionStore,
    *,
    confidence_low_threshold: float = 0.7,
    drift_threshold: float = 0.5,
    drift_confidence_level: float = 0.6,
) -> dict[str, Any]:
    """Generate a humility audit with warnings about pattern state."""
    all_patterns = pattern_store.query_patterns(
        {}, min_confidence=-1.0, exclude_anti_patterns=False
    )

    low_confidence_patterns = []
    untested_patterns = []
    risky_assumptions = []

    for pattern in all_patterns:
        confidence = pattern.get("confidence", 0.0)
        pattern_id: str = pattern.get("pattern_id", "")
        name = pattern.get("name", "Unknown")

        if confidence < confidence_low_threshold:
            low_confidence_patterns.append(
                {
                    "pattern_id": pattern_id,
                    "name": name,
                    "confidence": confidence,
                    "reason": (
                        f"Confidence {confidence:.2f} below threshold {confidence_low_threshold}"
                    ),
                }
            )

        decisions = decision_store.get_decisions_for_pattern(pattern_id)
        if not decisions:
            untested_patterns.append(
                {
                    "pattern_id": pattern_id,
                    "name": name,
                    "last_tested_context": None,
                }
            )

        if confidence < 0.5:
            risky_assumptions.append(
                {
                    "assumption": f"Pattern '{name}' is reliable",
                    "why_risky": f"Confidence is only {confidence:.2f}",
                    "mitigation": "Validate with more evidence before recommending",
                }
            )

    total_patterns = len(all_patterns)
    low_confidence_count = sum(
        1 for p in all_patterns if p.get("confidence", 0.0) < drift_confidence_level
    )
    drift_ratio = low_confidence_count / total_patterns if total_patterns > 0 else 0.0
    drift_detected = drift_ratio > drift_threshold

    pattern_gaps = []
    if not all_patterns:
        pattern_gaps.append(
            {
                "gap_type": "no_patterns",
                "description": "No patterns have been learned yet",
            }
        )

    audit = {
        "low_confidence_patterns": low_confidence_patterns,
        "untested_patterns": untested_patterns,
        "pattern_gaps": pattern_gaps,
        "risky_assumptions": risky_assumptions,
        "drift_detected": drift_detected,
        "drift_reason": (
            f"{low_confidence_count}/{total_patterns} patterns "
            f"({drift_ratio * 100:.1f}%) below confidence {drift_confidence_level}"
        )
        if drift_detected
        else None,
    }

    logger.info(
        f"Generated humility audit: "
        f"{len(low_confidence_patterns)} low-confidence, "
        f"{len(untested_patterns)} untested, "
        f"drift_detected={drift_detected}"
    )
    return audit
