"""Decision storage and retrieval for the agent learning loop.

This module provides the DecisionStore class for persisting decisions to the ledger
and retrieving them. All decisions are stored as AGENT_DECISION events in the DivineOS
ledger with SHA256 hashing for integrity.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from divineos.core.ledger import log_event, get_events


class DecisionStore:
    """Stores and retrieves decisions from the DivineOS ledger.

    All decisions are persisted as AGENT_DECISION events with SHA256 hashing.
    Decisions capture the agent's choice of pattern, alternatives considered,
    and counterfactual analysis.
    """

    def __init__(self) -> None:
        """Initialize the decision store."""
        self.logger = logger

    def store_decision(
        self,
        session_id: str,
        task: str,
        chosen_pattern: str,
        pattern_confidence: float,
        alternatives_considered: list[dict[str, Any]],
        counterfactual: dict[str, Any],
        outcome: Optional[dict[str, Any]] = None,
    ) -> str:
        """Store a decision to the ledger as an AGENT_DECISION event.

        Args:
            session_id: Session ID this decision is for
            task: Description of what decision was made
            chosen_pattern: Pattern ID of the chosen pattern
            pattern_confidence: Confidence score of the chosen pattern
            alternatives_considered: List of alternatives considered
                Each item: {pattern_id, name, confidence, why_rejected}
            counterfactual: Counterfactual analysis
                {chosen_cost, alternative_costs, default_cost, counterfactual_type}
            outcome: Optional outcome information (populated after work completes)
                {success, primary_outcome, violations_introduced, token_efficiency, rework_needed}

        Returns:
            Decision ID (UUID)

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not session_id:
            raise ValueError("session_id is required")

        if not task:
            raise ValueError("task is required")

        if not chosen_pattern:
            raise ValueError("chosen_pattern is required")

        if not -1.0 <= pattern_confidence <= 1.0:
            raise ValueError(
                f"pattern_confidence must be between -1.0 and 1.0, got {pattern_confidence}"
            )

        if not isinstance(alternatives_considered, list):
            raise ValueError("alternatives_considered must be a list")

        if not isinstance(counterfactual, dict):
            raise ValueError("counterfactual must be a dict")

        if "chosen_cost" not in counterfactual:
            raise ValueError("counterfactual must include chosen_cost")

        if "alternative_costs" not in counterfactual:
            raise ValueError("counterfactual must include alternative_costs")

        if "default_cost" not in counterfactual:
            raise ValueError("counterfactual must include default_cost")

        if "counterfactual_type" not in counterfactual:
            raise ValueError("counterfactual must include counterfactual_type")

        if counterfactual["counterfactual_type"] not in ("estimated", "measured"):
            raise ValueError(
                f"counterfactual_type must be 'estimated' or 'measured', "
                f"got {counterfactual['counterfactual_type']}"
            )

        if outcome is not None:
            if not isinstance(outcome, dict):
                raise ValueError("outcome must be a dict")

            if "success" not in outcome:
                raise ValueError("outcome must include success")

            if not isinstance(outcome["success"], bool):
                raise ValueError("outcome.success must be a bool")

            if "primary_outcome" not in outcome:
                raise ValueError("outcome must include primary_outcome")

            if "violations_introduced" not in outcome:
                raise ValueError("outcome must include violations_introduced")

            if "token_efficiency" not in outcome:
                raise ValueError("outcome must include token_efficiency")

            if "rework_needed" not in outcome:
                raise ValueError("outcome must include rework_needed")

            if not isinstance(outcome["rework_needed"], bool):
                raise ValueError("outcome.rework_needed must be a bool")

        decision_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "decision_id": decision_id,
            "session_id": session_id,
            "timestamp": now,
            "task": task,
            "chosen_pattern": chosen_pattern,
            "pattern_confidence": pattern_confidence,
            "alternatives_considered": alternatives_considered,
            "counterfactual": counterfactual,
            "outcome": outcome,
        }

        # Compute SHA256 hash of decision content for integrity (truncated to 32 chars like ledger)
        decision_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(decision_json.encode()).hexdigest()[:32]
        payload["content_hash"] = content_hash

        try:
            log_event(
                event_type="AGENT_DECISION",
                actor="agent",
                payload=payload,
                validate=False,
            )
            self.logger.info(
                f"Stored decision {decision_id} for session {session_id} "
                f"(pattern: {chosen_pattern}, confidence: {pattern_confidence})"
            )
            return decision_id
        except Exception as e:
            self.logger.error(f"Failed to store decision: {e}")
            raise

    def get_decisions_for_pattern(self, pattern_id: str) -> list[dict[str, Any]]:
        """Retrieve all decisions using a specific pattern.

        Returns all AGENT_DECISION events where the chosen_pattern matches the given pattern_id.
        Results are sorted by timestamp (most recent first).

        Args:
            pattern_id: Pattern ID to search for

        Returns:
            List of decision dictionaries sorted by timestamp (most recent first)
        """
        try:
            events = get_events(event_type="AGENT_DECISION", limit=10000)

            # Find all decisions using this pattern
            matching_decisions: list[dict[str, Any]] = []
            for e in events:
                payload = e.get("payload")
                if payload is not None and payload.get("chosen_pattern") == pattern_id:
                    matching_decisions.append(payload)

            # Sort by timestamp (most recent first)
            matching_decisions.sort(key=lambda d: d.get("timestamp", ""), reverse=True)

            self.logger.info(
                f"Found {len(matching_decisions)} decisions using pattern {pattern_id}"
            )
            return matching_decisions
        except Exception as e:
            self.logger.error(f"Failed to get decisions for pattern {pattern_id}: {e}")
            return []
