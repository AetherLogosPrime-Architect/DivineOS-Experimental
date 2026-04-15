"""Automatic agent memory monitoring and persistence.

This module runs as part of DivineOS and automatically:
1. Monitors token usage during agent work
2. Saves work checkpoints to the ledger
3. Compresses context when approaching token limits
4. Loads previous work context on session start
5. Runs learning cycles at session end
6. Provides pattern recommendations for new work
7. Records work outcomes for pattern validation

This is NOT an IDE hook - it's part of the OS itself.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from divineos.agent_integration.learning_cycle import LearningCycle
from divineos.agent_integration.pattern_recommender import PatternRecommender
from divineos.core.ledger import get_events, get_recent_context, log_event

_MM_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


class AgentMemoryMonitor:
    """Automatic memory monitoring for agent work sessions."""

    # Token budget and thresholds
    # IDE compresses at 80%, so we must save before that
    TOTAL_BUDGET = 200_000
    COMPRESSION_THRESHOLD = int(TOTAL_BUDGET * 0.75)  # 150,000 tokens
    WARNING_THRESHOLD = int(TOTAL_BUDGET * 0.65)  # 130,000 tokens

    def __init__(self, session_id: str):
        """Initialize memory monitor for a session.

        Args:
            session_id: Unique identifier for this work session
        """
        self.session_id = session_id
        self.current_tokens = 0
        self.last_checkpoint_tokens = 0
        self.compression_triggered = False
        self.context_loaded = False

        logger.info(f"AgentMemoryMonitor initialized for session: {session_id}")

        # DO NOT auto-load context on initialization - this causes infinite loops
        # Context must be loaded explicitly via load_session_context() when needed

    def load_session_context(self) -> dict[str, Any]:
        """Load work context from ledger for this session.

        Returns:
            Dictionary with session context including previous work
        """
        try:
            # Query ledger for AGENT_WORK events from this session
            events = get_events(event_type="AGENT_WORK", actor="agent")

            # Filter to this session
            session_events = [
                e for e in events if e.get("payload", {}).get("session_id") == self.session_id
            ]

            # Get recent context for reference
            recent = get_recent_context(n=20)

            context = {
                "session_id": self.session_id,
                "previous_work": session_events,
                "recent_context": recent,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(f"Loaded session context: {len(session_events)} previous work items")
            return context
        except _MM_ERRORS as e:
            logger.error(f"Failed to load session context: {e}")
            return {
                "session_id": self.session_id,
                "previous_work": [],
                "recent_context": [],
                "error": str(e),
            }

    def update_token_usage(self, current_tokens: int) -> dict[str, Any]:
        """Update token usage and check thresholds.

        This is called automatically by the OS to monitor token usage.

        Args:
            current_tokens: Current token count

        Returns:
            Dictionary with status and any actions needed
        """
        self.current_tokens = current_tokens
        remaining = self.TOTAL_BUDGET - current_tokens
        usage_percent = (current_tokens / self.TOTAL_BUDGET) * 100

        status: dict[str, Any] = {
            "current_tokens": current_tokens,
            "remaining_tokens": remaining,
            "usage_percent": usage_percent,
            "action": None,
        }

        if current_tokens >= self.COMPRESSION_THRESHOLD and not self.compression_triggered:
            status["action"] = "COMPRESS_NOW"
            status["message"] = (
                f"Token usage at {usage_percent:.1f}% - "
                "Saving work to ledger and compressing context"
            )
            self.compression_triggered = True
            logger.warning(f"Compression threshold reached: {usage_percent:.1f}%")

        elif current_tokens >= self.WARNING_THRESHOLD:
            status["action"] = "PREPARE_COMPRESSION"
            status["message"] = (
                f"Token usage at {usage_percent:.1f}% - Prepare to save work and compress context"
            )
            logger.warning(f"Warning threshold reached: {usage_percent:.1f}%")

        return status

    def save_work_checkpoint(
        self,
        task: str,
        status: str,
        files_modified: list[str],
        tests_passing: int,
        commit_hash: Optional[str] = None,
        notes: str = "",
    ) -> str:
        """Save a work checkpoint to the ledger.

        This is called automatically by the OS after major work is completed.

        Args:
            task: Name of the task completed
            status: Status (in_progress, completed, failed)
            files_modified: List of files that were modified
            tests_passing: Number of tests passing
            commit_hash: Git commit hash if applicable
            notes: Additional notes about the work

        Returns:
            Event ID from ledger
        """
        try:
            payload = {
                "session_id": self.session_id,
                "task": task,
                "status": status,
                "files_modified": files_modified,
                "tests_passing": tests_passing,
                "commit_hash": commit_hash,
                "notes": notes,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "token_usage": self.current_tokens,
            }

            event_id = log_event(
                event_type="AGENT_WORK",
                actor="agent",
                payload=payload,
                validate=False,
            )

            self.last_checkpoint_tokens = self.current_tokens
            logger.info(f"Saved work checkpoint: {task} (event_id: {event_id})")
            return event_id
        except _MM_ERRORS as e:
            logger.error(f"Failed to save work checkpoint: {e}")
            raise

    def compress_context(self, summary: str) -> str:
        """Compress context by saving summary to ledger.

        This is called automatically by the OS when approaching token limits.

        Args:
            summary: Summary of work completed in this session

        Returns:
            Event ID from ledger
        """
        try:
            payload = {
                "session_id": self.session_id,
                "type": "context_compression",
                "summary": summary,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "token_usage_at_compression": self.current_tokens,
            }

            event_id = log_event(
                event_type="AGENT_CONTEXT_COMPRESSION",
                actor="agent",
                payload=payload,
                validate=False,
            )

            logger.info(
                f"Context compressed at {self.current_tokens} tokens (event_id: {event_id})"
            )
            return event_id
        except _MM_ERRORS as e:
            logger.error(f"Failed to compress context: {e}")
            raise

    def run_learning_cycle(self) -> dict[str, Any]:
        """Run the learning cycle at session end.

        This analyzes work history, extracts patterns, updates confidence scores,
        and generates a humility audit for the next session.

        Returns:
            Dictionary with learning cycle results including audit_id
        """
        try:
            logger.info(f"Starting learning cycle for session: {self.session_id}")

            cycle = LearningCycle()
            results = cycle.run(self.session_id)

            logger.info(
                f"Learning cycle completed: {results['patterns_extracted']} patterns extracted, "
                f"audit_id: {results['audit_id']}"
            )
            return results
        except _MM_ERRORS as e:
            logger.error(f"Failed to run learning cycle: {e}")
            return {
                "session_id": self.session_id,
                "error": str(e),
                "patterns_extracted": 0,
                "audit_id": None,
            }

    def get_recommendation(self, context: dict[str, Any]) -> dict[str, Any]:
        """Get a pattern recommendation for new work.

        This loads the humility audit, queries patterns matching the current context,
        and returns a recommendation with reasoning.

        Args:
            context: Current context (phase, token_budget, codebase_structure, etc.)

        Returns:
            Recommendation dictionary with pattern_id, confidence, explanation, etc.
        """
        try:
            logger.info(f"Getting recommendation for context: {context}")

            recommender = PatternRecommender()

            # Load humility audit (displays warnings)
            audit = recommender.load_humility_audit()
            if audit:
                logger.info(
                    f"Loaded humility audit: {len(audit.get('low_confidence_patterns', []))} "
                    f"low-confidence patterns"
                )

            # Generate recommendation
            recommendation = recommender.generate_recommendation(context)

            if recommendation:
                logger.info(
                    f"Generated recommendation: {recommendation['pattern_name']} "
                    f"(confidence: {recommendation['confidence']})"
                )
                return recommendation
            else:
                logger.warning("No recommendation generated")
                return {
                    "pattern_id": "fallback",
                    "pattern_name": "Generic Approach",
                    "confidence": 0.3,
                    "explanation": "No recommendation available",
                }
        except _MM_ERRORS as e:
            logger.error(f"Failed to get recommendation: {e}")
            return {
                "pattern_id": "fallback",
                "pattern_name": "Generic Approach",
                "confidence": 0.3,
                "error": str(e),
                "explanation": "Failed to generate recommendation due to error",
            }

    def record_work_outcome(
        self,
        task: str,
        pattern_id: str,
        success: bool,
        violations_introduced: int = 0,
        token_efficiency: float = 0.0,
        rework_needed: bool = False,
    ) -> str:
        """Record the outcome of work after it completes.

        This measures the outcome (success/failure, violations, token efficiency, rework)
        and stores it in the ledger for pattern validation.

        Args:
            task: Task that was completed
            pattern_id: Pattern ID that was used (or "fallback" if no pattern)
            success: Whether the work succeeded
            violations_introduced: Number of new violations introduced
            token_efficiency: Tokens used / outcome value
            rework_needed: Whether rework is needed

        Returns:
            Event ID from ledger
        """
        try:
            logger.info(
                f"Recording work outcome: task={task}, pattern={pattern_id}, "
                f"success={success}, violations={violations_introduced}"
            )

            # Build outcome record
            outcome = {
                "success": success,
                "primary_outcome": "completed" if success else "failed",
                "violations_introduced": violations_introduced,
                "token_efficiency": token_efficiency,
                "rework_needed": rework_needed,
            }

            payload = {
                "session_id": self.session_id,
                "task": task,
                "pattern_id": pattern_id,
                "outcome": outcome,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            event_id = log_event(
                event_type="AGENT_WORK_OUTCOME",
                actor="agent",
                payload=payload,
                validate=False,
            )

            logger.info(f"Recorded work outcome (event_id: {event_id})")
            return event_id
        except _MM_ERRORS as e:
            logger.error(f"Failed to record work outcome: {e}")
            raise

    def end_session(self, summary: str, final_status: str = "completed") -> str:
        """End the work session and save final state to ledger.

        This is called automatically by the OS when the session ends.
        It triggers the learning cycle to analyze work and extract patterns.

        Args:
            summary: Summary of work completed
            final_status: Final status (completed, paused, failed)

        Returns:
            Event ID from ledger
        """
        try:
            # Run learning cycle before ending session
            logger.info("Running learning cycle before session end")
            cycle_results = self.run_learning_cycle()

            payload = {
                "session_id": self.session_id,
                "type": "session_end",
                "summary": summary,
                "final_status": final_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "final_token_usage": self.current_tokens,
                "learning_cycle_results": cycle_results,
            }

            event_id = log_event(
                event_type="AGENT_SESSION_END",
                actor="agent",
                payload=payload,
                validate=False,
            )

            logger.info(f"Session ended: {final_status} (event_id: {event_id})")
            return event_id
        except _MM_ERRORS as e:
            logger.error(f"Failed to end session: {e}")
            raise
