"""Pattern storage and retrieval for the agent learning loop.

This module provides the PatternStore class for persisting patterns to the ledger
and querying them based on context. All patterns are stored as AGENT_PATTERN events
in the DivineOS ledger with SHA256 hashing for integrity.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from divineos.core.ledger import log_event, get_events


class PatternStore:
    """Stores and retrieves patterns from the DivineOS ledger.

    All patterns are persisted as AGENT_PATTERN events with SHA256 hashing.
    Patterns include preconditions for context-aware matching.
    """

    def __init__(self) -> None:
        """Initialize the pattern store."""
        self.logger = logger

    def store_pattern(
        self,
        pattern_type: str,
        name: str,
        description: str,
        preconditions: dict[str, Any],
        occurrences: int = 0,
        successes: int = 0,
        confidence: float = 0.0,
        source_events: Optional[list[str]] = None,
    ) -> str:
        """Store a pattern to the ledger as an AGENT_PATTERN event.

        Args:
            pattern_type: "structural" or "tactical"
            name: Human-readable pattern name
            description: Pattern description
            preconditions: Context conditions (token_budget_min, token_budget_max, phase, etc.)
            occurrences: Number of times observed
            successes: Number of times succeeded
            confidence: Confidence score (-1.0 to 1.0)
            source_events: Event IDs that contributed to this pattern

        Returns:
            Pattern ID (UUID)

        Raises:
            ValueError: If pattern_type is invalid or confidence out of range
        """
        if pattern_type not in ("structural", "tactical"):
            raise ValueError(f"Invalid pattern_type: {pattern_type}")

        if not -1.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be between -1.0 and 1.0, got {confidence}")

        if occurrences < 0 or successes < 0:
            raise ValueError("Occurrences and successes must be non-negative")

        if successes > occurrences:
            raise ValueError("Successes cannot exceed occurrences")

        pattern_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Calculate success rate
        success_rate = successes / occurrences if occurrences > 0 else 0.0

        payload = {
            "pattern_id": pattern_id,
            "pattern_type": pattern_type,
            "name": name,
            "description": description,
            "preconditions": preconditions,
            "occurrences": occurrences,
            "successes": successes,
            "success_rate": success_rate,
            "confidence": confidence,
            "last_validated": now,
            "decay_rate": 0.05 if pattern_type == "tactical" else 0.0,
            "source_events": source_events or [],
            "created_at": now,
            "updated_at": now,
        }

        # Compute SHA256 hash of pattern content for integrity (truncated to 32 chars like ledger)
        pattern_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(pattern_json.encode()).hexdigest()[:32]
        payload["content_hash"] = content_hash

        try:
            log_event(
                event_type="AGENT_PATTERN",
                actor="agent",
                payload=payload,
                validate=False,
            )
            self.logger.info(f"Stored pattern {pattern_id} ({name}) with confidence {confidence}")
            return pattern_id
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            raise

    def get_pattern(self, pattern_id: str) -> Optional[dict[str, Any]]:
        """Retrieve a pattern from the ledger by ID.

        Returns the most recent version of the pattern.

        Args:
            pattern_id: UUID of the pattern to retrieve

        Returns:
            Pattern dictionary or None if not found
        """
        try:
            events = get_events(event_type="AGENT_PATTERN", limit=10000)

            # Find all events for this pattern and return the most recent
            matching_events = [
                e for e in events if e.get("payload", {}).get("pattern_id") == pattern_id
            ]

            if not matching_events:
                return None

            # Return the last (most recent) event
            return matching_events[-1].get("payload")
        except Exception as e:
            self.logger.error(f"Failed to get pattern {pattern_id}: {e}")
            return None

    def query_patterns(
        self,
        preconditions: dict[str, Any],
        min_confidence: float = 0.65,
        exclude_anti_patterns: bool = True,
    ) -> list[dict[str, Any]]:
        """Query patterns matching the given preconditions.

        Filters patterns by context matching and confidence threshold.
        Anti-patterns (confidence < -0.5) are excluded by default.

        Args:
            preconditions: Current context (token_budget, phase, codebase_structure, etc.)
            min_confidence: Minimum confidence threshold (default 0.65)
            exclude_anti_patterns: If True, exclude patterns with confidence < -0.5

        Returns:
            List of matching patterns sorted by confidence (highest first)
        """
        try:
            events = get_events(event_type="AGENT_PATTERN", limit=10000)
            matched_patterns: list[dict[str, Any]] = []

            for event in events:
                payload = event.get("payload", {})
                confidence = payload.get("confidence", 0)

                # Skip anti-patterns if requested
                if exclude_anti_patterns and confidence < -0.5:
                    continue

                # Skip patterns below confidence threshold
                # (unless they're anti-patterns and we're including them)
                if not exclude_anti_patterns and confidence < -0.5:
                    # Anti-pattern: no min_confidence threshold
                    pass
                elif confidence < min_confidence:
                    # Regular pattern: apply min_confidence threshold
                    continue

                # Check if preconditions match
                if self._preconditions_match(payload.get("preconditions", {}), preconditions):
                    matched_patterns.append(payload)

            # Sort by confidence (highest first)
            matched_patterns.sort(key=lambda p: p.get("confidence", 0), reverse=True)

            self.logger.info(
                f"Query returned {len(matched_patterns)} patterns matching preconditions"
            )
            return matched_patterns
        except Exception as e:
            self.logger.error(f"Failed to query patterns: {e}")
            return []

    def update_pattern_confidence(
        self,
        pattern_id: str,
        delta: float,
        reason: str,
        source_event_id: Optional[str] = None,
    ) -> bool:
        """Update a pattern's confidence score with logging.

        Creates a new AGENT_PATTERN event with updated confidence.
        Logs the reasoning for the update.

        Args:
            pattern_id: UUID of the pattern to update
            delta: Confidence delta to apply (-1.0 to 1.0)
            reason: Reason for the update (logged for transparency)
            source_event_id: Event ID that triggered this update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current pattern
            pattern = self.get_pattern(pattern_id)
            if not pattern:
                self.logger.error(f"Pattern {pattern_id} not found")
                return False

            # Calculate new confidence (clamped to [-1.0, 1.0])
            old_confidence = pattern.get("confidence", 0.0)
            new_confidence = max(-1.0, min(1.0, old_confidence + delta))

            # Update pattern
            pattern["confidence"] = new_confidence
            pattern["updated_at"] = datetime.now(timezone.utc).isoformat()

            # Track source event if provided
            if source_event_id:
                source_events = pattern.get("source_events", [])
                if source_event_id not in source_events:
                    source_events.append(source_event_id)
                    pattern["source_events"] = source_events

            # Recompute hash
            pattern_json = json.dumps(pattern, sort_keys=True, ensure_ascii=False)
            content_hash = hashlib.sha256(pattern_json.encode()).hexdigest()[:32]
            pattern["content_hash"] = content_hash

            # Store updated pattern
            log_event(
                event_type="AGENT_PATTERN",
                actor="agent",
                payload=pattern,
                validate=False,
            )

            # Log the update with reasoning
            log_event(
                event_type="AGENT_PATTERN_UPDATE",
                actor="agent",
                payload={
                    "pattern_id": pattern_id,
                    "old_confidence": old_confidence,
                    "new_confidence": new_confidence,
                    "delta": delta,
                    "reason": reason,
                    "source_event_id": source_event_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                validate=False,
            )

            self.logger.info(
                f"Updated pattern {pattern_id} confidence: {old_confidence} → {new_confidence} "
                f"(delta: {delta:+.2f}, reason: {reason})"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to update pattern confidence: {e}")
            return False

    def _preconditions_match(
        self, pattern_preconditions: dict[str, Any], current_context: dict[str, Any]
    ) -> bool:
        """Check if pattern preconditions match current context.

        Preconditions are optional - if not specified, they match any context.
        Token budget ranges are inclusive.

        Args:
            pattern_preconditions: Preconditions from the pattern
            current_context: Current context to match against

        Returns:
            True if all specified preconditions match
        """
        # Token budget range check
        if "token_budget_min" in pattern_preconditions:
            min_budget = pattern_preconditions["token_budget_min"]
            current_budget = current_context.get("token_budget", 0)
            if current_budget < min_budget:
                return False

        if "token_budget_max" in pattern_preconditions:
            max_budget = pattern_preconditions["token_budget_max"]
            current_budget = current_context.get("token_budget", 0)
            if current_budget > max_budget:
                return False

        # Phase check
        if "phase" in pattern_preconditions:
            pattern_phase = pattern_preconditions["phase"]
            current_phase = current_context.get("phase")
            if current_phase != pattern_phase:
                return False

        # Codebase structure check
        if "codebase_structure" in pattern_preconditions:
            pattern_structure = pattern_preconditions["codebase_structure"]
            current_structure = current_context.get("codebase_structure")
            if current_structure != pattern_structure:
                return False

        # Constraints check (all constraints must be satisfied)
        if "constraints" in pattern_preconditions:
            pattern_constraints = pattern_preconditions["constraints"]
            current_constraints = current_context.get("constraints", [])
            for constraint in pattern_constraints:
                if constraint not in current_constraints:
                    return False

        return True
