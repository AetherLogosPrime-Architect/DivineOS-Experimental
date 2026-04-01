"""Module-level convenience functions and singleton management for AgentMemoryMonitor.

Provides get_memory_monitor() singleton access and end_session()
that delegate to the global monitor instance.
"""

import threading


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


def end_session(summary: str, final_status: str = "completed") -> str:
    """End the session."""
    if _monitor is None:
        raise RuntimeError("Monitor not initialized")
    return _monitor.end_session(summary, final_status)
