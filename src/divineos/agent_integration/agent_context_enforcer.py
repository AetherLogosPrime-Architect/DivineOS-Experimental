"""Enforces automatic memory system usage in agent execution.

This module provides the structural enforcement that ensures the agent
ALWAYS loads context at startup and records work to the ledger after
completion. This is not optional - it's built into the execution path.
"""

from typing import Any, Optional

from loguru import logger

from divineos.agent_integration.memory_monitor import get_memory_monitor
from divineos.core.ledger import get_ledger


class AgentContextEnforcer:
    """Enforces memory system usage in agent execution.

    This class ensures that:
    1. Context is loaded from ledger at session start
    2. Work is recorded to ledger after task completion
    3. The ledger becomes the source of truth for continuity
    """

    def __init__(self, session_id: str = "foundation-ledger-architecture-fix"):
        """Initialize the enforcer.

        Args:
            session_id: Session ID for memory tracking
        """
        self.session_id = session_id
        self.monitor = get_memory_monitor(session_id)
        self.ledger = get_ledger()
        self._context_loaded = False
        self._context: dict[str, Any] = {}

    def load_context_at_startup(self) -> dict[str, Any]:
        """Load context from ledger at session startup.

        This MUST be called before any agent work begins.

        Returns:
            Context dict with previous work, patterns, and recommendations
        """
        if self._context_loaded:
            logger.debug("Context already loaded in this session")
            return self._context

        logger.info("[ENFORCER] Loading context from ledger at startup")

        try:
            context = self.monitor.load_session_context()
            self._context = context
            self._context_loaded = True

            # Log what was loaded
            previous_work = context.get("previous_work", [])
            patterns = context.get("patterns", [])
            recommendations = context.get("recommendations", [])

            logger.info(
                f"[ENFORCER] Context loaded: {len(previous_work)} previous work items, "
                f"{len(patterns)} patterns, {len(recommendations)} recommendations"
            )

            return context

        except Exception as e:
            logger.error(f"[ENFORCER] Failed to load context: {e}")
            raise

    def record_work_after_completion(
        self,
        task: str,
        status: str = "completed",
        files_modified: Optional[list[str]] = None,
        tests_passing: int = 0,
        commit_hash: Optional[str] = None,
        notes: str = "",
    ) -> str:
        """Record work to ledger after task completion.

        This MUST be called after every task completion.

        Args:
            task: Task name
            status: Task status (completed, failed, paused)
            files_modified: List of modified files
            tests_passing: Number of passing tests
            commit_hash: Git commit hash if applicable
            notes: Additional notes

        Returns:
            Event ID in ledger
        """
        logger.info(f"[ENFORCER] Recording work to ledger: {task}")

        try:
            event_id = self.monitor.save_work_checkpoint(
                task=task,
                status=status,
                files_modified=files_modified or [],
                tests_passing=tests_passing,
                commit_hash=commit_hash,
                notes=notes,
            )

            logger.info(f"[ENFORCER] Work recorded: {task} (event_id: {event_id})")
            return event_id

        except Exception as e:
            logger.error(f"[ENFORCER] Failed to record work: {e}")
            raise

    def end_session(self, summary: str, final_status: str = "completed") -> str:
        """End session and save final state to ledger.

        Args:
            summary: Summary of work completed
            final_status: Final status (completed, paused, failed)

        Returns:
            Event ID in ledger
        """
        logger.info(f"[ENFORCER] Ending session: {self.session_id}")

        try:
            event_id = self.monitor.end_session(summary, final_status)
            logger.info(f"[ENFORCER] Session ended and recorded: {event_id}")
            return event_id

        except Exception as e:
            logger.error(f"[ENFORCER] Failed to end session: {e}")
            raise


# Global enforcer instance
_global_enforcer: Optional[AgentContextEnforcer] = None


def get_agent_context_enforcer(
    session_id: str = "foundation-ledger-architecture-fix",
) -> AgentContextEnforcer:
    """Get or create the global agent context enforcer.

    Args:
        session_id: Session ID for memory tracking

    Returns:
        AgentContextEnforcer instance
    """
    global _global_enforcer

    if _global_enforcer is None:
        _global_enforcer = AgentContextEnforcer(session_id)

    return _global_enforcer


def enforce_context_loading(
    session_id: str = "foundation-ledger-architecture-fix",
) -> dict[str, Any]:
    """Enforce context loading at agent startup.

    This MUST be called at the very beginning of agent execution.

    Args:
        session_id: Session ID for memory tracking

    Returns:
        Context dict loaded from ledger
    """
    logger.info("[ENFORCER] Enforcing context loading at startup")
    enforcer = get_agent_context_enforcer(session_id)
    context = enforcer.load_context_at_startup()
    logger.info("[ENFORCER] Context loading enforced")
    return context


def enforce_work_recording(
    task: str,
    status: str = "completed",
    files_modified: Optional[list[str]] = None,
    tests_passing: int = 0,
    commit_hash: Optional[str] = None,
    notes: str = "",
    session_id: str = "foundation-ledger-architecture-fix",
) -> str:
    """Enforce work recording to ledger after task completion.

    This MUST be called after every task completion.

    Args:
        task: Task name
        status: Task status
        files_modified: List of modified files
        tests_passing: Number of passing tests
        commit_hash: Git commit hash
        notes: Additional notes
        session_id: Session ID for memory tracking

    Returns:
        Event ID in ledger
    """
    logger.info("[ENFORCER] Enforcing work recording")
    enforcer = get_agent_context_enforcer(session_id)
    event_id = enforcer.record_work_after_completion(
        task=task,
        status=status,
        files_modified=files_modified,
        tests_passing=tests_passing,
        commit_hash=commit_hash,
        notes=notes,
    )
    logger.info("[ENFORCER] Work recording enforced")
    return event_id


def enforce_session_end(
    summary: str,
    final_status: str = "completed",
    session_id: str = "foundation-ledger-architecture-fix",
) -> str:
    """Enforce session end and save final state to ledger.

    This MUST be called at the very end of agent execution.

    Args:
        summary: Summary of work completed
        final_status: Final status
        session_id: Session ID for memory tracking

    Returns:
        Event ID in ledger
    """
    logger.info("[ENFORCER] Enforcing session end")
    enforcer = get_agent_context_enforcer(session_id)
    event_id = enforcer.end_session(summary, final_status)
    logger.info("[ENFORCER] Session end enforced")
    return event_id
