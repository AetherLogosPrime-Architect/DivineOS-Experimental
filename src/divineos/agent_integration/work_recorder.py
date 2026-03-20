"""Automatic work recording to ledger for agent learning.

This module provides decorators and utilities to automatically record
agent work to the ledger so the learning system has data to learn from.

DEPRECATED: Use agent_executor.py instead. This module is kept for backward
compatibility but all new code should use execute_agent_task() from agent_executor.
"""

from functools import wraps
from typing import Any, Callable

from loguru import logger

from divineos.agent_integration.memory_monitor import get_memory_monitor
from divineos.agent_integration.agent_executor import execute_agent_task


def record_work(task_name: str, session_id: str = "foundation-ledger-architecture-fix"):
    """Decorator to automatically record work completion to ledger.

    DEPRECATED: Use @with_memory_middleware from agent_middleware.py instead.

    Usage:
        @record_work("Fix datetime.UTC imports")
        def fix_datetime_imports():
            # do work
            return {"files_modified": [...], "tests_passing": 1499}

    Args:
        task_name: Name of the task being completed
        session_id: Session ID for the work
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Delegate to the executor
            return execute_agent_task(task_name, func, *args, session_id=session_id, **kwargs)

        return wrapper

    return decorator


def auto_record_session_end(
    summary: str,
    session_id: str = "foundation-ledger-architecture-fix",
    final_status: str = "completed",
):
    """Automatically record session end to ledger.

    DEPRECATED: Use finalize_agent_execution() from agent_executor.py instead.

    Args:
        summary: Summary of work completed
        session_id: Session ID
        final_status: Final status (completed, paused, failed)
    """
    try:
        monitor = get_memory_monitor(session_id)
        event_id = monitor.end_session(summary, final_status)
        logger.info(f"Session ended and recorded: {event_id}")
        return event_id
    except Exception as e:
        logger.error(f"Failed to record session end: {e}")
        raise
