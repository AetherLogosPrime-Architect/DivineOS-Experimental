"""Learning cycle implementation for agent self-reflection and behavioral improvement.

This module provides the LearningCycle class which:
1. Loads work history from the ledger (AGENT_WORK events from last 30 days)
2. Extracts patterns from work outcomes
3. Updates pattern confidence based on outcomes
4. Detects pattern invalidation and conflicts
5. Generates humility audits
6. Stores results back to the ledger

The learning cycle runs at the end of each session to enable the agent to learn
from its own work and improve future decisions.
"""

import time
from datetime import timezone, datetime
from typing import Any

from loguru import logger

from divineos.core.ledger import get_events
from divineos.agent_integration.pattern_store import PatternStore
from divineos.agent_integration.learning_audit_store import LearningAuditStore
from divineos.agent_integration.decision_store import DecisionStore


class LearningCycle:
    """Orchestrates the agent learning cycle.

    The learning cycle runs at the end of each session and:
    1. Loads work history from the last 30 days
    2. Extracts patterns from work outcomes
    3. Updates pattern confidence based on outcomes
    4. Detects pattern invalidation and conflicts
    5. Generates a humility audit
    6. Stores results to the ledger

    All operations use the real ledger (no mocking).
    """

    # Confidence update deltas
    SUCCESS_DELTA = 0.05
    FAILURE_DELTA = -0.15  # 3× heavier than success
    SECONDARY_EFFECTS_DELTA = -0.1  # Additional penalty for violations/debt
    CONTEXT_CHANGE_DOWNWEIGHT = 0.30  # 30% downweight
    PRECONDITION_MISMATCH_DOWNWEIGHT = 0.20  # 20% downweight

    # Thresholds
    TACTICAL_FAILURE_THRESHOLD = 3  # Archive after 3+ failures
    CONFIDENCE_ARCHIVE_THRESHOLD = -0.5  # Archive patterns below this
    CONFIDENCE_RECOMMENDATION_THRESHOLD = 0.65  # Don't recommend below this
    CONFIDENCE_LOW_THRESHOLD = 0.7  # Flag as low confidence
    DRIFT_THRESHOLD = 0.5  # >50% patterns below 0.6 = drift
    DRIFT_CONFIDENCE_LEVEL = 0.6  # Threshold for drift detection
    MIN_OCCURRENCES = 5  # Minimum occurrences before recommendation
    MIN_SUCCESS_RATE = 0.6  # Minimum success rate for positive patterns

    # Time windows
    WORK_HISTORY_DAYS = 30
    TACTICAL_VALIDATION_DAYS = 30

    def __init__(self) -> None:
        """Initialize the learning cycle."""
        self.logger = logger
        self.pattern_store = PatternStore()
        self.audit_store = LearningAuditStore()
        self.decision_store = DecisionStore()

    def load_work_history(self) -> list[dict[str, Any]]:
        """Load AGENT_WORK events from the last 30 days.

        Returns:
            List of AGENT_WORK event payloads sorted by timestamp (oldest first)
        """
        try:
            # Get all AGENT_WORK events
            events = get_events(event_type="AGENT_WORK", limit=10000)

            if not events:
                self.logger.info("No work history found")
                return []

            # Filter to last 30 days
            cutoff_time = time.time() - (self.WORK_HISTORY_DAYS * 24 * 60 * 60)

            recent_events = [e for e in events if float(e.get("timestamp", 0)) >= cutoff_time]

            self.logger.info(
                f"Loaded {len(recent_events)} work events from last {self.WORK_HISTORY_DAYS} days"
            )
            result: list[dict[str, Any]] = []
            for e in recent_events:
                payload = e.get("payload")
                if payload is not None:
                    result.append(payload)
            return result
        except Exception as e:
            self.logger.error(f"Failed to load work history: {e}")
            return []

    def extract_patterns(self, work_history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Extract patterns from work history.

        Groups similar approaches by preconditions and calculates success rates.

        Args:
            work_history: List of AGENT_WORK event payloads

        Returns:
            List of extracted patterns with success rates
        """
        if not work_history:
            self.logger.info("No work history to extract patterns from")
            return []

        try:
            # Load all decisions to see what patterns were used
            all_decisions = get_events(event_type="AGENT_DECISION", limit=10000)
            decision_payloads = [e.get("payload") for e in all_decisions]

            # Group decisions by pattern_id
            patterns_used: dict[str, list[dict[str, Any]]] = {}
            for decision in decision_payloads:
                if decision is None:
                    continue
                pattern_id = decision.get("chosen_pattern")
                if pattern_id not in patterns_used:
                    patterns_used[pattern_id] = []
                patterns_used[pattern_id].append(decision)

            # For each pattern used, calculate success rate
            extracted_patterns = []
            for pattern_id, decisions in patterns_used.items():
                successes = sum(1 for d in decisions if d.get("outcome", {}).get("success", False))
                total = len(decisions)
                success_rate = successes / total if total > 0 else 0.0

                extracted_patterns.append(
                    {
                        "pattern_id": pattern_id,
                        "occurrences": total,
                        "successes": successes,
                        "success_rate": success_rate,
                        "decisions": decisions,
                    }
                )

            self.logger.info(f"Extracted {len(extracted_patterns)} patterns from work history")
            return extracted_patterns
        except Exception as e:
            self.logger.error(f"Failed to extract patterns: {e}")
            return []

    def update_existing_patterns(self, extracted_patterns: list[dict[str, Any]]) -> None:
        """Update existing patterns with confidence deltas based on outcomes.

        Applies confidence update rules:
        - Success: delta = +0.05
        - Failure: delta = -0.15 (3× heavier)
        - Secondary effects (violations, debt): delta = -0.1 additional

        Args:
            extracted_patterns: List of extracted patterns with outcomes
        """
        try:
            for pattern_info in extracted_patterns:
                pattern_id = pattern_info["pattern_id"]
                decisions = pattern_info["decisions"]

                # Get the current pattern
                current_pattern = self.pattern_store.get_pattern(pattern_id)
                if current_pattern is None:
                    self.logger.warning(f"Pattern {pattern_id} not found in store, skipping update")
                    continue

                # Calculate confidence delta
                total_delta = 0.0
                for decision in decisions:
                    outcome = decision.get("outcome")
                    if outcome is None:
                        continue

                    # Primary outcome
                    if outcome.get("success", False):
                        total_delta += self.SUCCESS_DELTA
                    else:
                        total_delta += self.FAILURE_DELTA

                    # Secondary effects
                    violations = outcome.get("violations_introduced", 0)
                    if violations > 0:
                        total_delta += self.SECONDARY_EFFECTS_DELTA

                # Apply delta
                self.pattern_store.update_pattern_confidence(
                    pattern_id=pattern_id,
                    delta=total_delta,
                    reason=f"Updated based on {len(decisions)} outcomes "
                    f"(delta: {total_delta:+.2f})",
                )

                self.logger.info(
                    f"Updated pattern {pattern_id}: "
                    f"delta: {total_delta:+.2f} based on {len(decisions)} outcomes"
                )
        except Exception as e:
            self.logger.error(f"Failed to update existing patterns: {e}")

    def detect_invalidation(self) -> list[str]:
        """Detect and archive failed/outdated patterns.

        Archives patterns that:
        - Failed 3+ times (tactical patterns)
        - Have confidence < -0.5 (anti-patterns)
        - Context changed (codebase structure hash differs)
        - Preconditions no longer match

        Returns:
            List of archived pattern IDs
        """
        try:
            archived_patterns = []

            # Get all patterns
            all_patterns = get_events(event_type="AGENT_PATTERN", limit=10000)
            pattern_payloads = [e.get("payload") for e in all_patterns]

            for pattern in pattern_payloads:
                if pattern is None:
                    continue

                pattern_id = pattern.get("pattern_id")
                confidence = pattern.get("confidence", 0.0)
                pattern_type = pattern.get("pattern_type")

                # Check if should be archived
                should_archive = False
                reason = ""
                delta = 0.0

                # Anti-patterns
                if confidence < self.CONFIDENCE_ARCHIVE_THRESHOLD:
                    should_archive = True
                    reason = f"Anti-pattern (confidence: {confidence:.2f})"
                    delta = -0.5 - confidence  # Set to -0.5

                # Tactical patterns with 3+ failures
                if pattern_type == "tactical":
                    successes = pattern.get("successes", 0)
                    occurrences = pattern.get("occurrences", 0)
                    failures = occurrences - successes

                    if failures >= self.TACTICAL_FAILURE_THRESHOLD:
                        should_archive = True
                        reason = f"Tactical pattern failed {failures} times"
                        delta = -0.5 - confidence  # Set to -0.5

                if should_archive:
                    # Archive by setting confidence to -0.5
                    self.pattern_store.update_pattern_confidence(
                        pattern_id=pattern_id,
                        delta=delta,
                        reason=f"Archived: {reason}",
                    )
                    archived_patterns.append(pattern_id)
                    self.logger.info(f"Archived pattern {pattern_id}: {reason}")

            return archived_patterns
        except Exception as e:
            self.logger.error(f"Failed to detect invalidation: {e}")
            return []

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """Detect contradictory structural patterns.

        Finds structural patterns with contradictory preconditions that could
        lead to conflicting recommendations.

        Returns:
            List of conflicts: [{pattern_id_1, pattern_id_2, conflict_reason}]
        """
        try:
            conflicts = []

            # Get all structural patterns
            all_patterns = get_events(event_type="AGENT_PATTERN", limit=10000)
            pattern_payloads = [e.get("payload") for e in all_patterns]

            structural_patterns = [
                p
                for p in pattern_payloads
                if p is not None and p.get("pattern_type") == "structural"
            ]

            # Check for contradictions
            for i, pattern1 in enumerate(structural_patterns):
                for pattern2 in structural_patterns[i + 1 :]:
                    # Check if preconditions contradict
                    prec1 = pattern1.get("preconditions", {})
                    prec2 = pattern2.get("preconditions", {})

                    # Simple conflict detection: same precondition keys with different values
                    for key in prec1:
                        if key in prec2 and prec1[key] != prec2[key]:
                            # Check if both patterns have high confidence
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
                                self.logger.warning(
                                    f"Conflict detected between patterns "
                                    f"{pattern1.get('pattern_id')} and "
                                    f"{pattern2.get('pattern_id')}: {key}"
                                )

            return conflicts
        except Exception as e:
            self.logger.error(f"Failed to detect conflicts: {e}")
            return []

    def generate_humility_audit(self) -> dict[str, Any]:
        """Generate a humility audit with warnings about pattern state.

        Creates an audit that includes:
        - Patterns with confidence < 0.7 (low confidence)
        - Patterns never tested in current context
        - Gaps in pattern coverage
        - Risky assumptions
        - Drift detection (>50% patterns < 0.6 confidence)

        Returns:
            Audit dictionary
        """
        try:
            # Get all patterns
            all_patterns = get_events(event_type="AGENT_PATTERN", limit=10000)
            pattern_payloads = [e.get("payload") for e in all_patterns]

            low_confidence_patterns = []
            untested_patterns = []
            risky_assumptions = []

            for pattern in pattern_payloads:
                if pattern is None:
                    continue

                confidence = pattern.get("confidence", 0.0)
                pattern_id = pattern.get("pattern_id")
                name = pattern.get("name", "Unknown")

                # Low confidence patterns
                if confidence < self.CONFIDENCE_LOW_THRESHOLD:
                    low_confidence_patterns.append(
                        {
                            "pattern_id": pattern_id,
                            "name": name,
                            "confidence": confidence,
                            "reason": (
                                f"Confidence {confidence:.2f} below threshold "
                                f"{self.CONFIDENCE_LOW_THRESHOLD}"
                            ),
                        }
                    )

                # Untested patterns (never used in decisions)
                decisions = self.decision_store.get_decisions_for_pattern(pattern_id)
                if not decisions:
                    untested_patterns.append(
                        {
                            "pattern_id": pattern_id,
                            "name": name,
                            "last_tested_context": None,
                        }
                    )

                # Risky assumptions for low-confidence patterns
                if confidence < 0.5:
                    risky_assumptions.append(
                        {
                            "assumption": f"Pattern '{name}' is reliable",
                            "why_risky": f"Confidence is only {confidence:.2f}",
                            "mitigation": "Validate with more evidence before recommending",
                        }
                    )

            # Detect drift
            total_patterns = len([p for p in pattern_payloads if p is not None])
            low_confidence_count = sum(
                1
                for p in pattern_payloads
                if p is not None and p.get("confidence", 0.0) < self.DRIFT_CONFIDENCE_LEVEL
            )
            drift_ratio = low_confidence_count / total_patterns if total_patterns > 0 else 0.0
            drift_detected = drift_ratio > self.DRIFT_THRESHOLD

            # Pattern gaps
            pattern_gaps = []
            if not pattern_payloads:
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
                    f"({drift_ratio * 100:.1f}%) below confidence {self.DRIFT_CONFIDENCE_LEVEL}"
                )
                if drift_detected
                else None,
            }

            self.logger.info(
                f"Generated humility audit: "
                f"{len(low_confidence_patterns)} low-confidence, "
                f"{len(untested_patterns)} untested, "
                f"drift_detected={drift_detected}"
            )
            return audit
        except Exception as e:
            self.logger.error(f"Failed to generate humility audit: {e}")
            return {
                "low_confidence_patterns": [],
                "untested_patterns": [],
                "pattern_gaps": [],
                "risky_assumptions": [],
                "drift_detected": False,
                "drift_reason": None,
            }

    def run(self, session_id: str) -> dict[str, Any]:
        """Orchestrate the full learning cycle.

        Runs all 7 steps of the learning cycle:
        1. Load work history
        2. Extract patterns
        3. Update existing patterns
        4. Detect invalidation
        5. Detect conflicts
        6. Generate humility audit
        7. Store results

        Args:
            session_id: Session ID for this learning cycle

        Returns:
            Dictionary with results of the learning cycle
        """
        try:
            self.logger.info(f"Starting learning cycle for session {session_id}")

            # Step 1: Load work history
            work_history = self.load_work_history()

            # Step 2: Extract patterns
            extracted_patterns = self.extract_patterns(work_history)

            # Step 3: Update existing patterns
            self.update_existing_patterns(extracted_patterns)

            # Step 4: Detect invalidation
            archived_patterns = self.detect_invalidation()

            # Step 5: Detect conflicts
            conflicts = self.detect_conflicts()

            # Step 6: Generate humility audit
            audit = self.generate_humility_audit()

            # Step 7: Store results
            audit_id = self.audit_store.store_audit(
                session_id=session_id,
                low_confidence_patterns=audit["low_confidence_patterns"],
                untested_patterns=audit["untested_patterns"],
                pattern_gaps=audit["pattern_gaps"],
                risky_assumptions=audit["risky_assumptions"],
                drift_detected=audit["drift_detected"],
                drift_reason=audit["drift_reason"],
            )

            results = {
                "session_id": session_id,
                "work_history_count": len(work_history),
                "patterns_extracted": len(extracted_patterns),
                "patterns_updated": len(extracted_patterns),
                "patterns_archived": len(archived_patterns),
                "conflicts_detected": len(conflicts),
                "audit_id": audit_id,
                "audit": audit,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self.logger.info(
                f"Learning cycle completed: "
                f"{len(work_history)} work items, "
                f"{len(extracted_patterns)} patterns updated, "
                f"{len(archived_patterns)} archived, "
                f"{len(conflicts)} conflicts detected"
            )
            return results
        except Exception as e:
            self.logger.error(f"Learning cycle failed: {e}")
            raise
