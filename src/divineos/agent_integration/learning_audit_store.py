"""Learning audit storage and retrieval for the agent learning loop.

This module provides the LearningAuditStore class for persisting learning audits
to the ledger and retrieving them. All audits are stored as AGENT_LEARNING_AUDIT
events in the DivineOS ledger with SHA256 hashing for integrity.
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from divineos.core.ledger import log_event, get_events


class LearningAuditStore:
    """Stores and retrieves learning audits from the DivineOS ledger.

    All audits are persisted as AGENT_LEARNING_AUDIT events with SHA256 hashing.
    Audits capture the system's self-reflection on pattern confidence, gaps, and risks.
    """

    def __init__(self) -> None:
        """Initialize the learning audit store."""
        self.logger = logger

    def store_audit(
        self,
        session_id: str,
        low_confidence_patterns: list[dict[str, Any]],
        untested_patterns: list[dict[str, Any]],
        pattern_gaps: list[dict[str, Any]],
        risky_assumptions: list[dict[str, Any]],
        drift_detected: bool = False,
        drift_reason: Optional[str] = None,
    ) -> str:
        """Store a learning audit to the ledger as an AGENT_LEARNING_AUDIT event.

        Args:
            session_id: Session ID this audit is for
            low_confidence_patterns: List of patterns with confidence < 0.7
                Each item: {pattern_id, name, confidence, reason}
            untested_patterns: List of patterns never tested in current context
                Each item: {pattern_id, name, last_tested_context}
            pattern_gaps: List of identified gaps in pattern coverage
                Each item: {gap_type, description}
            risky_assumptions: List of risky assumptions underlying patterns
                Each item: {assumption, why_risky, mitigation}
            drift_detected: Whether system drift was detected (>50% patterns < 0.6 confidence)
            drift_reason: Reason for drift if detected

        Returns:
            Audit ID (UUID)

        Raises:
            ValueError: If required fields are missing or invalid
        """
        if not session_id:
            raise ValueError("session_id is required")

        if not isinstance(low_confidence_patterns, list):
            raise ValueError("low_confidence_patterns must be a list")

        if not isinstance(untested_patterns, list):
            raise ValueError("untested_patterns must be a list")

        if not isinstance(pattern_gaps, list):
            raise ValueError("pattern_gaps must be a list")

        if not isinstance(risky_assumptions, list):
            raise ValueError("risky_assumptions must be a list")

        if drift_detected and not drift_reason:
            raise ValueError("drift_reason is required when drift_detected is True")

        audit_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        payload = {
            "audit_id": audit_id,
            "session_id": session_id,
            "timestamp": now,
            "low_confidence_patterns": low_confidence_patterns,
            "untested_patterns": untested_patterns,
            "pattern_gaps": pattern_gaps,
            "risky_assumptions": risky_assumptions,
            "drift_detected": drift_detected,
            "drift_reason": drift_reason,
        }

        # Compute SHA256 hash of audit content for integrity (truncated to 32 chars like ledger)
        audit_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(audit_json.encode()).hexdigest()[:32]
        payload["content_hash"] = content_hash

        try:
            log_event(
                event_type="AGENT_LEARNING_AUDIT",
                actor="agent",
                payload=payload,
                validate=False,
            )
            self.logger.info(
                f"Stored learning audit {audit_id} for session {session_id} "
                f"(drift_detected={drift_detected})"
            )
            return audit_id
        except Exception as e:
            self.logger.error(f"Failed to store learning audit: {e}")
            raise

    def get_latest_audit(self) -> Optional[dict[str, Any]]:
        """Retrieve the most recent learning audit from the ledger.

        Returns the most recent AGENT_LEARNING_AUDIT event.

        Returns:
            Audit dictionary or None if no audits found
        """
        try:
            events = get_events(event_type="AGENT_LEARNING_AUDIT", limit=10000)

            if not events:
                return None

            # Return the last (most recent) event
            return events[-1].get("payload")
        except Exception as e:
            self.logger.error(f"Failed to get latest audit: {e}")
            return None
