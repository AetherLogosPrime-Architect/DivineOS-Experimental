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
from divineos.agent_integration.pattern_validation import (
    detect_invalidation as _detect_invalidation,
    detect_conflicts as _detect_conflicts,
    generate_humility_audit as _generate_humility_audit,
)

# Import monitoring
try:
    from divineos.integration.system_monitor import get_system_monitor

    HAS_MONITORING = True
except ImportError:
    HAS_MONITORING = False


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

    def capture_violation_event(self, violation_event: dict[str, Any]) -> None:
        """Capture a clarity violation event and update pattern store.

        Called by ClarityEnforcer when a violation is detected. Extracts the violation
        pattern and stores it to the pattern store with violation metadata.

        Args:
            violation_event: Dictionary with keys:
                - type: "CLARITY_VIOLATION"
                - session_id: Session ID
                - tool_name: Name of the tool that violated clarity
                - tool_input: Input to the tool
                - context: Context provided (may be empty, list, or string)
                - violation_type: Type of violation (e.g., "UNEXPLAINED_TOOL")
                - confidence: Confidence level of violation detection (0.0-1.0)
                - timestamp: When violation occurred
                - enforcement_mode: BLOCKING, LOGGING, or PERMISSIVE
        """
        try:
            tool_name = violation_event.get("tool_name", "unknown")
            context = violation_event.get("context", "")
            violation_type = violation_event.get("violation_type", "unknown")
            confidence = violation_event.get("confidence", 0.5)

            # Handle context as list or string
            if isinstance(context, list):
                context_str = " ".join(context) if context else ""
            else:
                context_str = str(context) if context else ""

            # Determine context type
            if not context_str or context_str.strip() == "":
                context_type = "empty"
            elif len(context_str) < 50:
                context_type = "minimal"
            else:
                context_type = "present"

            # Create pattern ID from tool and context type
            pattern_id = f"{tool_name}_{context_type}_{violation_type}"

            self.logger.info(
                f"Capturing violation: tool={tool_name}, context_type={context_type}, "
                f"violation_type={violation_type}, confidence={confidence}"
            )

            # Update pattern store with violation
            self.pattern_store.record_violation(
                pattern_id=pattern_id,
                tool_name=tool_name,
                context_type=context_type,
                violation_type=violation_type,
                confidence=confidence,
            )

            self.logger.info(f"Violation pattern recorded: {pattern_id}")

        except Exception as e:
            self.logger.error(f"Failed to capture violation event: {e}")

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
        """Detect and archive failed/outdated patterns. Delegates to pattern_validation."""
        try:
            return _detect_invalidation(
                self.pattern_store,
                failure_threshold=self.TACTICAL_FAILURE_THRESHOLD,
                confidence_archive_threshold=self.CONFIDENCE_ARCHIVE_THRESHOLD,
            )
        except Exception as e:
            self.logger.error(f"Failed to detect invalidation: {e}")
            return []

    def detect_conflicts(self) -> list[dict[str, Any]]:
        """Detect contradictory structural patterns. Delegates to pattern_validation."""
        try:
            return _detect_conflicts(self.pattern_store)
        except Exception as e:
            self.logger.error(f"Failed to detect conflicts: {e}")
            return []

    def generate_humility_audit(self) -> dict[str, Any]:
        """Generate a humility audit. Delegates to pattern_validation."""
        try:
            return _generate_humility_audit(
                self.pattern_store,
                self.decision_store,
                confidence_low_threshold=self.CONFIDENCE_LOW_THRESHOLD,
                drift_threshold=self.DRIFT_THRESHOLD,
                drift_confidence_level=self.DRIFT_CONFIDENCE_LEVEL,
            )
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
        import time

        start_time = time.time()
        monitor = get_system_monitor() if HAS_MONITORING else None

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

            # Record success in monitoring
            if monitor:
                latency_ms = (time.time() - start_time) * 1000
                monitor.record_latency(monitor.MEMORY_LEARNING, latency_ms)
                monitor.record_success(monitor.MEMORY_LEARNING)

            return results
        except Exception as e:
            self.logger.error(f"Learning cycle failed: {e}")
            if monitor:
                monitor.record_error(monitor.MEMORY_LEARNING, e)
            raise
