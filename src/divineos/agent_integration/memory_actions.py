"""Module-level convenience functions and singleton management for AgentMemoryMonitor.

Provides get_memory_monitor() singleton access and thin wrappers
(load_context, check_token_usage, save_checkpoint, compress, end_session)
that delegate to the global monitor instance.
"""

import threading
from typing import Any, Optional


# Global monitor instance (typed loosely to avoid circular import at module level)
_monitor = None
_monitor_lock = threading.Lock()


def get_memory_monitor(session_id: str):
    """Get or create the global memory monitor instance."""
    from divineos.agent_integration.memory_monitor import AgentMemoryMonitor

    global _monitor
    if _monitor is None:
        with _monitor_lock:
            if _monitor is None:
                _monitor = AgentMemoryMonitor(session_id)
    return _monitor


def load_context(session_id: str) -> dict[str, Any]:
    """Load work context from ledger. Called at session start."""
    monitor = get_memory_monitor(session_id)
    result: dict[str, Any] = monitor.load_session_context()
    return result


def check_token_usage(current_tokens: int) -> dict[str, Any]:
    """Check token usage and return status."""
    if _monitor is None:
        return {"error": "Monitor not initialized"}
    return _monitor.update_token_usage(current_tokens)


def save_checkpoint(
    task: str,
    status: str,
    files_modified: list[str],
    tests_passing: int,
    commit_hash: Optional[str] = None,
    notes: str = "",
) -> str:
    """Save a work checkpoint."""
    if _monitor is None:
        raise RuntimeError("Monitor not initialized")
    return _monitor.save_work_checkpoint(
        task, status, files_modified, tests_passing, commit_hash, notes
    )


def compress(summary: str) -> str:
    """Compress context when approaching token limits."""
    if _monitor is None:
        raise RuntimeError("Monitor not initialized")
    return _monitor.compress_context(summary)


def end_session(summary: str, final_status: str = "completed") -> str:
    """End the session."""
    if _monitor is None:
        raise RuntimeError("Monitor not initialized")
    return _monitor.end_session(summary, final_status)
